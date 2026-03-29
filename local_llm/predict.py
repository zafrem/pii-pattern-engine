#!/usr/bin/env python3
"""
Inference Script for Fine-tuned PII Detection LLM

Loads the QLoRA adapter and runs PII detection on input text.
Supports three modes: NER masking, binary classification, and category analysis.

Usage:
    # Interactive mode
    python predict.py --adapter_path ./output/pii-llama3-qlora/adapter

    # Single text
    python predict.py --adapter_path ./output/pii-llama3-qlora/adapter \
        --text "Call me at 010-1234-5678"

    # Batch from file
    python predict.py --adapter_path ./output/pii-llama3-qlora/adapter \
        --input_file texts.txt --output_file results.jsonl

    # Using merged model (no adapter needed)
    python predict.py --model_path ./output/pii-llama3-qlora/merged \
        --text "My SSN is 123-45-6789"
"""

import argparse
import json
import sys
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig


# ---------------------------------------------------------------------------
# System prompts (must match training)
# ---------------------------------------------------------------------------

SYSTEM_PROMPTS = {
    "ner": (
        "You are a PII detection expert. Identify all personally identifiable "
        "information in the given text and replace each instance with the "
        "appropriate tag: [NAME], [PHONE], [EMAIL], [SSN], [CREDIT_CARD], "
        "[ID_NUMBER], [IP_ADDRESS], [BANK_ACCOUNT], [ADDRESS], [DATE_OF_BIRTH], "
        "[CRYPTO_ADDRESS], [API_KEY], [PRIVATE_KEY], or [OTHER_PII]. "
        "If no PII is found, return the text unchanged."
    ),
    "classify": (
        "You are a security analyst. Determine whether the given text contains "
        "personally identifiable information (PII). Respond with exactly "
        "'PII_DETECTED' or 'NO_PII'."
    ),
    "category": (
        "You are a PII classification expert. Analyze the given text and identify "
        "what type(s) of PII it contains. Respond with a JSON object containing: "
        '"has_pii" (boolean), "pii_types" (list of detected types), '
        '"risk_level" (low/medium/high/critical), and "explanation" (brief reason).'
    ),
}

TASK_INSTRUCTIONS = {
    "ner": "Detect and mask all PII in the following text.",
    "classify": "Does the following text contain PII?",
    "category": "Classify the PII in the following text.",
}


def parse_args():
    parser = argparse.ArgumentParser(description="PII detection inference")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--adapter_path", type=str,
                       help="Path to LoRA adapter directory")
    group.add_argument("--model_path", type=str,
                       help="Path to merged model directory")

    parser.add_argument("--base_model", type=str,
                        default="meta-llama/Meta-Llama-3-8B-Instruct",
                        help="Base model (only needed with --adapter_path)")
    parser.add_argument("--task", type=str, default="ner",
                        choices=["ner", "classify", "category"],
                        help="Detection task type")
    parser.add_argument("--text", type=str, default=None,
                        help="Single text to analyze")
    parser.add_argument("--input_file", type=str, default=None,
                        help="File with one text per line")
    parser.add_argument("--output_file", type=str, default=None,
                        help="Output JSONL file")
    parser.add_argument("--max_new_tokens", type=int, default=512,
                        help="Maximum tokens to generate")
    parser.add_argument("--temperature", type=float, default=0.1,
                        help="Sampling temperature (lower = more deterministic)")
    parser.add_argument("--use_4bit", action="store_true", default=True,
                        help="Load in 4-bit quantization")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------

def load_model(args):
    """Load model (with or without adapter)."""

    if args.model_path:
        # Load merged model directly
        print(f"Loading merged model from {args.model_path}...")
        tokenizer = AutoTokenizer.from_pretrained(args.model_path)
        model = AutoModelForCausalLM.from_pretrained(
            args.model_path,
            device_map="auto",
            torch_dtype=torch.bfloat16,
        )
    else:
        # Load base model + LoRA adapter
        print(f"Loading base model: {args.base_model}")
        tokenizer = AutoTokenizer.from_pretrained(args.base_model)

        if args.use_4bit:
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_use_double_quant=True,
            )
            model = AutoModelForCausalLM.from_pretrained(
                args.base_model,
                quantization_config=bnb_config,
                device_map="auto",
            )
        else:
            model = AutoModelForCausalLM.from_pretrained(
                args.base_model,
                device_map="auto",
                torch_dtype=torch.bfloat16,
            )

        # Load adapter
        print(f"Loading adapter from {args.adapter_path}...")
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, args.adapter_path)

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model.eval()
    return model, tokenizer


# ---------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------

def build_messages(text, task):
    """Build chat messages for the given task."""
    return [
        {"role": "system", "content": SYSTEM_PROMPTS[task]},
        {"role": "user", "content": f"{TASK_INSTRUCTIONS[task]}\n\n{text}"},
    ]


def predict(model, tokenizer, text, task="ner", max_new_tokens=512, temperature=0.1):
    """Run inference on a single text."""
    messages = build_messages(text, task)

    input_text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )

    inputs = tokenizer(input_text, return_tensors="pt").to(model.device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            do_sample=temperature > 0,
            top_p=0.9,
            repetition_penalty=1.1,
            pad_token_id=tokenizer.pad_token_id,
        )

    # Decode only the generated tokens (skip the input)
    generated = outputs[0][inputs["input_ids"].shape[1]:]
    response = tokenizer.decode(generated, skip_special_tokens=True).strip()

    return response


def predict_batch(model, tokenizer, texts, task="ner", **kwargs):
    """Run inference on multiple texts."""
    results = []
    for i, text in enumerate(texts):
        response = predict(model, tokenizer, text, task, **kwargs)
        results.append({
            "input": text,
            "task": task,
            "output": response,
        })
        if (i + 1) % 10 == 0:
            print(f"  Processed {i + 1}/{len(texts)}")
    return results


# ---------------------------------------------------------------------------
# Interactive mode
# ---------------------------------------------------------------------------

def interactive_mode(model, tokenizer, args):
    """Run interactive PII detection."""
    print("\n" + "=" * 60)
    print("PII Detection - Interactive Mode")
    print(f"Task: {args.task}")
    print("Type 'quit' to exit, 'task <name>' to switch tasks")
    print("=" * 60 + "\n")

    task = args.task

    while True:
        try:
            text = input("Input > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not text:
            continue
        if text.lower() == "quit":
            break
        if text.lower().startswith("task "):
            new_task = text.split(maxsplit=1)[1].strip()
            if new_task in SYSTEM_PROMPTS:
                task = new_task
                print(f"Switched to task: {task}")
            else:
                print(f"Unknown task. Available: {list(SYSTEM_PROMPTS.keys())}")
            continue

        response = predict(
            model, tokenizer, text, task,
            max_new_tokens=args.max_new_tokens,
            temperature=args.temperature,
        )
        print(f"\nResult ({task}):\n{response}\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = parse_args()

    model, tokenizer = load_model(args)

    if args.text:
        # Single text mode
        response = predict(
            model, tokenizer, args.text, args.task,
            max_new_tokens=args.max_new_tokens,
            temperature=args.temperature,
        )
        print(f"\nInput: {args.text}")
        print(f"Task:  {args.task}")
        print(f"Result:\n{response}")

    elif args.input_file:
        # Batch mode
        texts = Path(args.input_file).read_text().strip().splitlines()
        print(f"Processing {len(texts)} texts...")
        results = predict_batch(
            model, tokenizer, texts, args.task,
            max_new_tokens=args.max_new_tokens,
            temperature=args.temperature,
        )

        if args.output_file:
            with open(args.output_file, "w", encoding="utf-8") as f:
                for r in results:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            print(f"Results saved to {args.output_file}")
        else:
            for r in results:
                print(json.dumps(r, ensure_ascii=False, indent=2))

    else:
        # Interactive mode
        interactive_mode(model, tokenizer, args)


if __name__ == "__main__":
    main()
