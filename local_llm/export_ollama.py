#!/usr/bin/env python3
"""
Export Fine-tuned Model to Ollama / GGUF Format

Converts the merged model to GGUF format for deployment with Ollama or llama.cpp.

Usage:
    # Step 1: Merge LoRA adapter into base model
    python export_ollama.py merge \
        --base_model meta-llama/Meta-Llama-3-8B-Instruct \
        --adapter_path ./output/pii-llama3-qlora/adapter \
        --output_dir ./output/pii-llama3-merged

    # Step 2: Convert to GGUF (requires llama.cpp)
    python export_ollama.py convert \
        --model_dir ./output/pii-llama3-merged \
        --output_file ./output/pii-llama3.gguf \
        --quantize q4_k_m

    # Step 3: Create Ollama model
    python export_ollama.py ollama \
        --gguf_file ./output/pii-llama3.gguf \
        --model_name pii-detector
"""

import argparse
import subprocess
import sys
from pathlib import Path
from textwrap import dedent


def parse_args():
    parser = argparse.ArgumentParser(description="Export model for Ollama deployment")
    sub = parser.add_subparsers(dest="command", required=True)

    # Merge command
    merge_p = sub.add_parser("merge", help="Merge LoRA adapter into base model")
    merge_p.add_argument("--base_model", type=str, required=True)
    merge_p.add_argument("--adapter_path", type=str, required=True)
    merge_p.add_argument("--output_dir", type=str, required=True)

    # Convert command
    conv_p = sub.add_parser("convert", help="Convert to GGUF format")
    conv_p.add_argument("--model_dir", type=str, required=True,
                        help="Path to merged model directory")
    conv_p.add_argument("--output_file", type=str, required=True,
                        help="Output GGUF file path")
    conv_p.add_argument("--quantize", type=str, default="q4_k_m",
                        choices=["f16", "q8_0", "q5_k_m", "q4_k_m", "q4_0", "q3_k_m"],
                        help="Quantization type")
    conv_p.add_argument("--llama_cpp_path", type=str, default=None,
                        help="Path to llama.cpp directory")

    # Ollama command
    ollama_p = sub.add_parser("ollama", help="Create Ollama model from GGUF")
    ollama_p.add_argument("--gguf_file", type=str, required=True)
    ollama_p.add_argument("--model_name", type=str, default="pii-detector")
    ollama_p.add_argument("--task", type=str, default="ner",
                          choices=["ner", "classify", "category"])

    return parser.parse_args()


def cmd_merge(args):
    """Merge LoRA adapter weights into the base model."""
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    print(f"Loading base model: {args.base_model}")
    tokenizer = AutoTokenizer.from_pretrained(args.base_model)
    model = AutoModelForCausalLM.from_pretrained(
        args.base_model,
        device_map="cpu",
        torch_dtype=torch.float16,
    )

    print(f"Loading adapter: {args.adapter_path}")
    model = PeftModel.from_pretrained(model, args.adapter_path)

    print("Merging weights...")
    model = model.merge_and_unload()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Saving merged model to {output_dir}")
    model.save_pretrained(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    print("Merge complete!")


def cmd_convert(args):
    """Convert merged model to GGUF format using llama.cpp."""
    llama_cpp = args.llama_cpp_path
    if llama_cpp is None:
        # Try to find llama.cpp in common locations
        candidates = [
            Path.home() / "llama.cpp",
            Path.home() / "src" / "llama.cpp",
            Path("/opt/llama.cpp"),
        ]
        for c in candidates:
            if (c / "convert_hf_to_gguf.py").exists():
                llama_cpp = str(c)
                break

    if not llama_cpp:
        print("ERROR: llama.cpp not found. Please specify --llama_cpp_path")
        print("Install: git clone https://github.com/ggerganov/llama.cpp")
        sys.exit(1)

    convert_script = Path(llama_cpp) / "convert_hf_to_gguf.py"
    quantize_bin = Path(llama_cpp) / "build" / "bin" / "llama-quantize"

    if not convert_script.exists():
        print(f"ERROR: {convert_script} not found")
        sys.exit(1)

    output_file = Path(args.output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    if args.quantize == "f16":
        # Direct conversion to f16 GGUF
        print(f"Converting to GGUF (f16)...")
        subprocess.run([
            sys.executable, str(convert_script),
            args.model_dir,
            "--outfile", str(output_file),
            "--outtype", "f16",
        ], check=True)
    else:
        # Convert to f16 first, then quantize
        f16_file = output_file.with_suffix(".f16.gguf")

        print("Converting to GGUF (f16 intermediate)...")
        subprocess.run([
            sys.executable, str(convert_script),
            args.model_dir,
            "--outfile", str(f16_file),
            "--outtype", "f16",
        ], check=True)

        print(f"Quantizing to {args.quantize}...")
        if not quantize_bin.exists():
            print(f"ERROR: {quantize_bin} not found. Build llama.cpp first:")
            print(f"  cd {llama_cpp} && cmake -B build && cmake --build build")
            sys.exit(1)

        subprocess.run([
            str(quantize_bin),
            str(f16_file),
            str(output_file),
            args.quantize,
        ], check=True)

        # Clean up intermediate file
        f16_file.unlink()

    print(f"GGUF model saved to {output_file}")
    print(f"File size: {output_file.stat().st_size / 1e9:.2f} GB")


def cmd_ollama(args):
    """Create an Ollama model from a GGUF file."""
    from generate_instruct_data import SYSTEM_PROMPTS, TASK_INSTRUCTIONS

    # Pick system prompt based on task
    system_prompts = {
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
            "what type(s) of PII it contains. Respond with a JSON object."
        ),
    }

    system_prompt = system_prompts[args.task]

    # Create Modelfile
    modelfile_content = dedent(f"""\
        FROM {args.gguf_file}

        PARAMETER temperature 0.1
        PARAMETER top_p 0.9
        PARAMETER repeat_penalty 1.1
        PARAMETER num_predict 512

        SYSTEM \"\"\"{system_prompt}\"\"\"
    """)

    modelfile_path = Path(args.gguf_file).parent / "Modelfile"
    modelfile_path.write_text(modelfile_content)

    print(f"Modelfile created at {modelfile_path}")
    print(f"\nTo create the Ollama model, run:")
    print(f"  ollama create {args.model_name} -f {modelfile_path}")
    print(f"\nTo test:")
    print(f'  ollama run {args.model_name} "My SSN is 123-45-6789"')
    print(f"\nTo use via API:")
    print(f'  curl http://localhost:11434/api/generate -d \'{{"model": "{args.model_name}", "prompt": "Detect PII: My email is test@example.com"}}\'')


def main():
    args = parse_args()
    if args.command == "merge":
        cmd_merge(args)
    elif args.command == "convert":
        cmd_convert(args)
    elif args.command == "ollama":
        cmd_ollama(args)


if __name__ == "__main__":
    main()
