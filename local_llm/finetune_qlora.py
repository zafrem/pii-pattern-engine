#!/usr/bin/env python3
"""
QLoRA Fine-tuning Script for Llama 3 PII Detection

Fine-tunes Llama 3 (8B) using QLoRA for PII detection tasks.
Supports: NER masking, binary classification, and category classification.

Usage:
    # Basic fine-tuning
    python finetune_qlora.py

    # Custom model and output
    python finetune_qlora.py \
        --base_model meta-llama/Meta-Llama-3-8B-Instruct \
        --output_dir ./output/pii-llama3-qlora \
        --epochs 3 \
        --batch_size 4

    # Resume from checkpoint
    python finetune_qlora.py --resume_from ./output/pii-llama3-qlora/checkpoint-500
"""

import argparse
import json
import os
from pathlib import Path

import torch
from datasets import load_dataset
from peft import (
    LoraConfig,
    TaskType,
    get_peft_model,
    prepare_model_for_kbit_training,
)
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
)
from trl import SFTTrainer, SFTConfig


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_BASE_MODEL = "meta-llama/Meta-Llama-3-8B-Instruct"
DEFAULT_OUTPUT_DIR = str(Path(__file__).parent / "output" / "pii-llama3-qlora")
DEFAULT_DATA_DIR = str(Path(__file__).parent / "data")

# LoRA hyperparameters
LORA_R = 16              # Rank - higher = more capacity, more memory
LORA_ALPHA = 32          # Scaling factor (usually 2x rank)
LORA_DROPOUT = 0.05      # Dropout for regularization
LORA_TARGET_MODULES = [   # Llama 3 attention + MLP layers
    "q_proj", "k_proj", "v_proj", "o_proj",
    "gate_proj", "up_proj", "down_proj",
]

# Training defaults
MAX_SEQ_LENGTH = 1024
LEARNING_RATE = 2e-4
WEIGHT_DECAY = 0.01
WARMUP_RATIO = 0.03
GRADIENT_ACCUMULATION_STEPS = 4


def parse_args():
    parser = argparse.ArgumentParser(description="QLoRA fine-tuning for PII detection")
    parser.add_argument("--base_model", type=str, default=DEFAULT_BASE_MODEL,
                        help="Base model name or path")
    parser.add_argument("--output_dir", type=str, default=DEFAULT_OUTPUT_DIR,
                        help="Output directory for model and checkpoints")
    parser.add_argument("--data_dir", type=str, default=DEFAULT_DATA_DIR,
                        help="Directory containing train.jsonl and val.jsonl")
    parser.add_argument("--epochs", type=int, default=3,
                        help="Number of training epochs")
    parser.add_argument("--batch_size", type=int, default=4,
                        help="Per-device batch size")
    parser.add_argument("--max_seq_length", type=int, default=MAX_SEQ_LENGTH,
                        help="Maximum sequence length")
    parser.add_argument("--lr", type=float, default=LEARNING_RATE,
                        help="Learning rate")
    parser.add_argument("--lora_r", type=int, default=LORA_R,
                        help="LoRA rank")
    parser.add_argument("--lora_alpha", type=int, default=LORA_ALPHA,
                        help="LoRA alpha")
    parser.add_argument("--resume_from", type=str, default=None,
                        help="Resume training from checkpoint path")
    parser.add_argument("--use_4bit", action="store_true", default=True,
                        help="Use 4-bit quantization (QLoRA)")
    parser.add_argument("--use_8bit", action="store_true", default=False,
                        help="Use 8-bit quantization instead of 4-bit")
    parser.add_argument("--bf16", action="store_true", default=True,
                        help="Use bfloat16 precision")
    parser.add_argument("--gradient_checkpointing", action="store_true", default=True,
                        help="Enable gradient checkpointing to save memory")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Model loading with quantization
# ---------------------------------------------------------------------------

def load_quantized_model(model_name, args):
    """Load model with QLoRA quantization config."""
    print(f"Loading base model: {model_name}")

    if args.use_8bit:
        bnb_config = BitsAndBytesConfig(
            load_in_8bit=True,
        )
    else:
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",           # NormalFloat4 quantization
            bnb_4bit_compute_dtype=torch.bfloat16 if args.bf16 else torch.float16,
            bnb_4bit_use_double_quant=True,       # Nested quantization for extra savings
        )

    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
        torch_dtype=torch.bfloat16 if args.bf16 else torch.float16,
    )

    # Prepare for k-bit training
    model = prepare_model_for_kbit_training(
        model,
        use_gradient_checkpointing=args.gradient_checkpointing,
    )

    return model


def apply_lora(model, args):
    """Apply LoRA adapters to the model."""
    lora_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=LORA_DROPOUT,
        target_modules=LORA_TARGET_MODULES,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
    )

    model = get_peft_model(model, lora_config)

    # Print trainable parameters
    trainable, total = model.get_nb_trainable_parameters()
    print(f"Trainable parameters: {trainable:,} / {total:,} "
          f"({100 * trainable / total:.2f}%)")

    return model


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_tokenizer(model_name):
    """Load and configure the tokenizer."""
    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        trust_remote_code=True,
    )

    # Llama 3 uses a special pad token setup
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.pad_token_id = tokenizer.eos_token_id

    tokenizer.padding_side = "right"
    return tokenizer


def format_chat(example, tokenizer):
    """Format a single example using the chat template."""
    messages = example["messages"]
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=False,
    )
    return {"text": text}


def load_data(data_dir, tokenizer):
    """Load JSONL datasets and apply chat template formatting."""
    data_dir = Path(data_dir)

    data_files = {}
    if (data_dir / "train.jsonl").exists():
        data_files["train"] = str(data_dir / "train.jsonl")
    if (data_dir / "val.jsonl").exists():
        data_files["validation"] = str(data_dir / "val.jsonl")

    if not data_files:
        raise FileNotFoundError(
            f"No data files found in {data_dir}. "
            "Run generate_instruct_data.py first."
        )

    dataset = load_dataset("json", data_files=data_files)

    # Apply chat template
    dataset = dataset.map(
        lambda x: format_chat(x, tokenizer),
        remove_columns=dataset["train"].column_names,
    )

    print(f"Dataset loaded:")
    for split, ds in dataset.items():
        print(f"  {split}: {len(ds)} examples")

    return dataset


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def create_training_args(args):
    """Create training arguments."""
    return SFTConfig(
        output_dir=args.output_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS,
        learning_rate=args.lr,
        weight_decay=WEIGHT_DECAY,
        warmup_ratio=WARMUP_RATIO,
        lr_scheduler_type="cosine",
        bf16=args.bf16,
        fp16=not args.bf16,
        logging_steps=10,
        eval_strategy="steps",
        eval_steps=100,
        save_strategy="steps",
        save_steps=200,
        save_total_limit=3,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        report_to="none",  # Set to "wandb" or "tensorboard" if desired
        max_seq_length=args.max_seq_length,
        packing=False,
        dataset_text_field="text",
        gradient_checkpointing=args.gradient_checkpointing,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        optim="paged_adamw_8bit",  # Memory-efficient optimizer
    )


def train(model, tokenizer, dataset, args):
    """Run the training loop."""
    training_args = create_training_args(args)

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset["train"],
        eval_dataset=dataset.get("validation"),
        args=training_args,
    )

    # Resume from checkpoint if specified
    resume_from = args.resume_from
    if resume_from and Path(resume_from).exists():
        print(f"Resuming from checkpoint: {resume_from}")
        trainer.train(resume_from_checkpoint=resume_from)
    else:
        trainer.train()

    return trainer


# ---------------------------------------------------------------------------
# Save and export
# ---------------------------------------------------------------------------

def save_model(trainer, tokenizer, output_dir):
    """Save the fine-tuned LoRA adapter and tokenizer."""
    output_dir = Path(output_dir)

    # Save LoRA adapter
    adapter_dir = output_dir / "adapter"
    trainer.model.save_pretrained(str(adapter_dir))
    tokenizer.save_pretrained(str(adapter_dir))

    print(f"\nModel saved to {adapter_dir}/")
    print("To load the adapter for inference:")
    print(f"  from peft import PeftModel")
    print(f'  model = PeftModel.from_pretrained(base_model, "{adapter_dir}")')


def merge_and_save(model, tokenizer, output_dir):
    """Merge LoRA weights into base model and save (optional, for deployment)."""
    output_dir = Path(output_dir) / "merged"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Merging LoRA weights into base model...")
    merged_model = model.merge_and_unload()
    merged_model.save_pretrained(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    print(f"Merged model saved to {output_dir}/")
    print("This model can be loaded directly or converted to GGUF for Ollama/llama.cpp")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = parse_args()

    print("=" * 60)
    print("QLoRA Fine-tuning: Llama 3 for PII Detection")
    print("=" * 60)
    print(f"Base model:  {args.base_model}")
    print(f"Output:      {args.output_dir}")
    print(f"Data:        {args.data_dir}")
    print(f"Epochs:      {args.epochs}")
    print(f"Batch size:  {args.batch_size}")
    print(f"LoRA rank:   {args.lora_r}")
    print(f"Quantization: {'8-bit' if args.use_8bit else '4-bit (QLoRA)'}")
    print()

    # Check GPU
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        gpu_mem = torch.cuda.get_device_properties(0).total_mem / 1e9
        print(f"GPU: {gpu_name} ({gpu_mem:.1f} GB)")
    elif torch.backends.mps.is_available():
        print("Device: Apple Silicon (MPS)")
        print("Note: bitsandbytes QLoRA requires CUDA. Consider using MLX instead.")
    else:
        print("WARNING: No GPU detected. Training will be extremely slow.")
    print()

    # Load tokenizer
    tokenizer = load_tokenizer(args.base_model)

    # Load data
    dataset = load_data(args.data_dir, tokenizer)

    # Load quantized model
    model = load_quantized_model(args.base_model, args)

    # Apply LoRA
    model = apply_lora(model, args)

    # Train
    trainer = train(model, tokenizer, dataset, args)

    # Save
    save_model(trainer, tokenizer, args.output_dir)

    # Save training config for reproducibility
    config = {
        "base_model": args.base_model,
        "lora_r": args.lora_r,
        "lora_alpha": args.lora_alpha,
        "lora_dropout": LORA_DROPOUT,
        "target_modules": LORA_TARGET_MODULES,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "learning_rate": args.lr,
        "max_seq_length": args.max_seq_length,
        "quantization": "8bit" if args.use_8bit else "4bit-nf4",
    }
    config_path = Path(args.output_dir) / "training_config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    print("\nTraining complete!")
    print(f"Config saved to {config_path}")


if __name__ == "__main__":
    main()
