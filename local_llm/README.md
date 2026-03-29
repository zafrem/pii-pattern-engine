# Local LLM Fine-tuning for PII Detection

Fine-tune Llama 3 (or similar models) to detect and classify personally identifiable information (PII) using QLoRA.

## Why LLM for PII Detection?

While regex patterns catch structured PII (SSN, phone numbers), LLMs excel at:
- **Context-dependent detection**: Is "12345" a ZIP code or a product ID?
- **Unstructured PII**: Names, addresses, free-text medical records
- **Multi-language support**: Korean, Chinese, Japanese PII in natural text
- **Edge cases**: Obfuscated PII like "my ssn is one two three..."

## Architecture

```
pattern-engine/
├── regex/          # Rule-based patterns (fast, precise)
├── ml/             # sklearn classifiers (medium speed, good accuracy)
└── local_llm/      # LLM fine-tuning (slower, best contextual understanding)
    ├── generate_instruct_data.py   # Create training dataset
    ├── finetune_qlora.py           # QLoRA fine-tuning script
    ├── predict.py                  # Inference (interactive/batch)
    ├── evaluate.py                 # Model evaluation
    └── export_ollama.py            # Export to Ollama/GGUF
```

## Data Storage

Generated training data contains realistic fake PII and **must not be committed to the repository**. All scripts support `--output_dir` / `--data_dir` flags to store data outside the repo.

```bash
# Recommended: store data outside the repository
export PII_DATA_DIR=~/pii-datasets/local_llm

# Generate data to external directory
python generate_instruct_data.py --output_dir $PII_DATA_DIR

# Fine-tune using external data
python finetune_qlora.py --data_dir $PII_DATA_DIR

# Evaluate using external data
python evaluate.py --adapter_path ./output/pii-llama3-qlora/adapter \
    --test_data $PII_DATA_DIR/test.jsonl
```

If no `--output_dir` is specified, data is saved to `local_llm/data/` by default (git-ignored).

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Generate Training Data

```bash
# Save to external directory (recommended)
python generate_instruct_data.py --output_dir ~/pii-datasets/local_llm

# Or use the default (local_llm/data/, git-ignored)
python generate_instruct_data.py

# Control sample volume
python generate_instruct_data.py --output_dir ~/pii-datasets/local_llm --samples_per_pattern 50
```

This creates instruction-tuning data in four task formats:
- **NER**: Detect and mask PII → `"My SSN is 123-45-6789"` → `"My SSN is [SSN]"`
- **BIO**: Token-level BIO tagging for NER training
- **Classification**: Binary PII detection → `PII_DETECTED` / `NO_PII`
- **Category**: Detailed PII analysis → JSON with type, risk level, region

### 3. Fine-tune with QLoRA

```bash
# Basic (requires CUDA GPU with ~16GB VRAM)
python finetune_qlora.py --data_dir ~/pii-datasets/local_llm

# Custom settings
python finetune_qlora.py \
    --data_dir ~/pii-datasets/local_llm \
    --base_model meta-llama/Meta-Llama-3-8B-Instruct \
    --epochs 3 \
    --batch_size 4 \
    --lora_r 16 \
    --lr 2e-4
```

**GPU Requirements:**
| Model | QLoRA (4-bit) | LoRA (8-bit) | Full |
|-------|--------------|-------------|------|
| Llama 3 8B | ~6 GB | ~10 GB | ~32 GB |
| Llama 3 70B | ~40 GB | ~70 GB | ~280 GB |

### 4. Run Inference

```bash
# Interactive mode
python predict.py --adapter_path ./output/pii-llama3-qlora/adapter

# Single text
python predict.py \
    --adapter_path ./output/pii-llama3-qlora/adapter \
    --task ner \
    --text "My name is John and my SSN is 123-45-6789"

# Batch processing
python predict.py \
    --adapter_path ./output/pii-llama3-qlora/adapter \
    --input_file texts.txt \
    --output_file results.jsonl
```

### 5. Evaluate

```bash
python evaluate.py \
    --adapter_path ./output/pii-llama3-qlora/adapter \
    --test_data ~/pii-datasets/local_llm/test.jsonl \
    --output eval_results.json
```

### 6. Deploy with Ollama

```bash
# Merge LoRA adapter
python export_ollama.py merge \
    --base_model meta-llama/Meta-Llama-3-8B-Instruct \
    --adapter_path ./output/pii-llama3-qlora/adapter \
    --output_dir ./output/pii-llama3-merged

# Convert to GGUF
python export_ollama.py convert \
    --model_dir ./output/pii-llama3-merged \
    --output_file ./output/pii-llama3.gguf \
    --quantize q4_k_m

# Create Ollama model
python export_ollama.py ollama \
    --gguf_file ./output/pii-llama3.gguf \
    --model_name pii-detector

# Test
ollama run pii-detector "My email is john@example.com and SSN is 123-45-6789"
```

## Training Data Format

Each example uses the Llama 3 chat template:

```json
{
  "messages": [
    {"role": "system", "content": "You are a PII detection expert..."},
    {"role": "user", "content": "Detect and mask all PII in the following text.\n\nMy phone is 010-1234-5678"},
    {"role": "assistant", "content": "My phone is [PHONE]"}
  ]
}
```

## Supported PII Types

| Category | Examples | Risk Level |
|----------|----------|------------|
| SSN / RRN | US SSN, Korean RRN | Critical |
| Credit Cards | Visa, Mastercard, Amex | Critical |
| API Keys | AWS, Google Cloud, Stripe, Slack | Critical |
| Government IDs | Passport, Aadhaar, My Number, Driver License | High |
| Bank Accounts | IBAN, KR/CN/JP/TW bank numbers | High |
| Phone Numbers | US, KR, CN, JP, TW, IN (mobile & landline) | Medium |
| Email | All formats | Medium |
| Names | Korean, Chinese, Japanese names | Medium |
| IP Addresses | IPv4 | Medium |
| URLs / Dates | HTTP(S) URLs, ISO/slash dates | Low |

## Recommended Workflow

1. **Baseline**: Test vanilla Llama 3 with few-shot prompting
2. **Fine-tune**: QLoRA with ~3000+ examples if baseline is insufficient
3. **Evaluate**: Measure Precision/Recall/F1 on held-out test set
4. **Deploy**: Export to Ollama for production use
5. **Iterate**: Add more training data for weak categories

## Alternative Models

This pipeline also works with:
- **Llama 3.1** (8B/70B) - recommended for best performance
- **Mistral** (7B) - good alternative, smaller footprint
- **Qwen2** (7B) - strong multilingual (CJK) support
- **Gemma 2** (9B) - Google's open model

For Apple Silicon (M1/M2/M3), consider using [MLX](https://github.com/ml-explore/mlx) instead of bitsandbytes for quantization.
