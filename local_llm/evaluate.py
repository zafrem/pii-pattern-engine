#!/usr/bin/env python3
"""
Evaluation Script for Fine-tuned PII Detection LLM

Evaluates the model on the test set and reports:
- Binary classification: Precision, Recall, F1
- NER masking: Exact match accuracy, partial match rate
- Category classification: Per-category F1, confusion matrix

Usage:
    python evaluate.py \
        --adapter_path ./output/pii-llama3-qlora/adapter \
        --test_data ./data/test.jsonl
"""

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import torch
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)


def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate PII detection model")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--adapter_path", type=str)
    group.add_argument("--model_path", type=str)

    parser.add_argument("--base_model", type=str,
                        default="meta-llama/Meta-Llama-3-8B-Instruct")
    parser.add_argument("--test_data", type=str, required=True,
                        help="Path to test.jsonl")
    parser.add_argument("--max_samples", type=int, default=None,
                        help="Limit number of test samples")
    parser.add_argument("--output", type=str, default=None,
                        help="Save detailed results to JSONL")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Evaluation by task type
# ---------------------------------------------------------------------------

def detect_task_type(messages):
    """Detect task type from system prompt."""
    system_msg = messages[0]["content"] if messages[0]["role"] == "system" else ""
    if "mask" in system_msg.lower() or "replace" in system_msg.lower():
        return "ner"
    elif "PII_DETECTED" in system_msg:
        return "classify"
    elif "pii_types" in system_msg:
        return "category"
    return "unknown"


def evaluate_classification(predictions, references):
    """Evaluate binary classification results."""
    pred_labels = []
    ref_labels = []

    for pred, ref in zip(predictions, references):
        ref_label = 1 if "PII_DETECTED" in ref else 0
        pred_label = 1 if "PII_DETECTED" in pred else 0
        ref_labels.append(ref_label)
        pred_labels.append(pred_label)

    acc = accuracy_score(ref_labels, pred_labels)
    prec = precision_score(ref_labels, pred_labels, zero_division=0)
    rec = recall_score(ref_labels, pred_labels, zero_division=0)
    f1 = f1_score(ref_labels, pred_labels, zero_division=0)

    print("\n--- Binary Classification ---")
    print(f"  Accuracy:  {acc:.4f}")
    print(f"  Precision: {prec:.4f}")
    print(f"  Recall:    {rec:.4f}")
    print(f"  F1 Score:  {f1:.4f}")

    return {"accuracy": acc, "precision": prec, "recall": rec, "f1": f1}


def evaluate_ner(predictions, references):
    """Evaluate NER masking results."""
    exact_match = 0
    partial_match = 0
    total = len(predictions)

    pii_tags = re.compile(r"\[(?:NAME|PHONE|EMAIL|SSN|CREDIT_CARD|ID_NUMBER|"
                          r"IP_ADDRESS|BANK_ACCOUNT|ADDRESS|DATE_OF_BIRTH|"
                          r"CRYPTO_ADDRESS|API_KEY|PRIVATE_KEY|OTHER_PII|"
                          r"FINANCIAL_ID|IBAN|VAT_NUMBER|MEDICAL_ID|URL|DATE)\]")

    for pred, ref in zip(predictions, references):
        pred_clean = pred.strip()
        ref_clean = ref.strip()

        if pred_clean == ref_clean:
            exact_match += 1
            partial_match += 1
        else:
            # Check if the same PII tags appear
            pred_tags = set(pii_tags.findall(pred_clean))
            ref_tags = set(pii_tags.findall(ref_clean))
            if pred_tags and ref_tags and pred_tags == ref_tags:
                partial_match += 1

    em_rate = exact_match / max(total, 1)
    pm_rate = partial_match / max(total, 1)

    print("\n--- NER Masking ---")
    print(f"  Exact match:   {em_rate:.4f} ({exact_match}/{total})")
    print(f"  Partial match: {pm_rate:.4f} ({partial_match}/{total})")

    return {"exact_match": em_rate, "partial_match": pm_rate, "total": total}


def evaluate_category(predictions, references):
    """Evaluate category classification results."""
    pred_categories = []
    ref_categories = []
    parse_errors = 0

    for pred, ref in zip(predictions, references):
        try:
            ref_data = json.loads(ref)
            ref_cat = ref_data.get("pii_types", ["unknown"])[0] if ref_data.get("has_pii") else "none"
        except json.JSONDecodeError:
            ref_cat = "parse_error"

        try:
            pred_data = json.loads(pred)
            pred_cat = pred_data.get("pii_types", ["unknown"])[0] if pred_data.get("has_pii") else "none"
        except json.JSONDecodeError:
            pred_cat = "parse_error"
            parse_errors += 1

        ref_categories.append(ref_cat)
        pred_categories.append(pred_cat)

    acc = accuracy_score(ref_categories, pred_categories)
    f1_macro = f1_score(ref_categories, pred_categories, average="macro", zero_division=0)
    f1_weighted = f1_score(ref_categories, pred_categories, average="weighted", zero_division=0)

    print("\n--- Category Classification ---")
    print(f"  Accuracy:      {acc:.4f}")
    print(f"  F1 (macro):    {f1_macro:.4f}")
    print(f"  F1 (weighted): {f1_weighted:.4f}")
    print(f"  JSON parse errors: {parse_errors}/{len(predictions)}")

    return {
        "accuracy": acc, "f1_macro": f1_macro, "f1_weighted": f1_weighted,
        "parse_errors": parse_errors,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = parse_args()

    # Load model
    from predict import load_model, predict

    # Build args namespace for load_model
    class ModelArgs:
        pass
    model_args = ModelArgs()
    model_args.adapter_path = args.adapter_path
    model_args.model_path = args.model_path
    model_args.base_model = args.base_model
    model_args.use_4bit = True

    model, tokenizer = load_model(model_args)

    # Load test data
    print(f"Loading test data from {args.test_data}...")
    test_examples = []
    with open(args.test_data, "r", encoding="utf-8") as f:
        for line in f:
            test_examples.append(json.loads(line))

    if args.max_samples:
        test_examples = test_examples[:args.max_samples]

    print(f"Evaluating {len(test_examples)} examples...")

    # Group by task type
    task_groups = defaultdict(lambda: {"preds": [], "refs": [], "inputs": []})

    for i, example in enumerate(test_examples):
        messages = example["messages"]
        task_type = detect_task_type(messages)

        # Extract expected output (last assistant message)
        expected = messages[-1]["content"]

        # Extract user input
        user_msg = [m for m in messages if m["role"] == "user"][0]["content"]
        # Extract just the input text (after the instruction)
        input_text = user_msg.split("\n\n", 1)[-1] if "\n\n" in user_msg else user_msg

        # Get prediction
        prediction = predict(
            model, tokenizer, input_text, task_type,
            max_new_tokens=512, temperature=0.0,
        )

        task_groups[task_type]["preds"].append(prediction)
        task_groups[task_type]["refs"].append(expected)
        task_groups[task_type]["inputs"].append(input_text)

        if (i + 1) % 50 == 0:
            print(f"  Progress: {i + 1}/{len(test_examples)}")

    # Evaluate each task
    all_metrics = {}

    if "classify" in task_groups:
        g = task_groups["classify"]
        all_metrics["classify"] = evaluate_classification(g["preds"], g["refs"])

    if "ner" in task_groups:
        g = task_groups["ner"]
        all_metrics["ner"] = evaluate_ner(g["preds"], g["refs"])

    if "category" in task_groups:
        g = task_groups["category"]
        all_metrics["category"] = evaluate_category(g["preds"], g["refs"])

    # Summary
    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)
    for task, metrics in all_metrics.items():
        print(f"\n{task}:")
        for k, v in metrics.items():
            if isinstance(v, float):
                print(f"  {k}: {v:.4f}")
            else:
                print(f"  {k}: {v}")

    # Save detailed results
    if args.output:
        results = {
            "metrics": all_metrics,
            "details": [],
        }
        for task, g in task_groups.items():
            for inp, pred, ref in zip(g["inputs"], g["preds"], g["refs"]):
                results["details"].append({
                    "task": task,
                    "input": inp,
                    "prediction": pred,
                    "reference": ref,
                    "correct": pred.strip() == ref.strip(),
                })

        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\nDetailed results saved to {args.output}")


if __name__ == "__main__":
    main()
