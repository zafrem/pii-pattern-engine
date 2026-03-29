#!/usr/bin/env python3
"""
PII Detection Inference

Loads trained models and predicts whether input text contains PII,
and if so, what category it belongs to.
"""

import csv
import json
import pickle
import sys
from pathlib import Path

import numpy as np

DEFAULT_MODEL_DIR = Path(__file__).parent / "models"
DEFAULT_DATA_DIR = Path(__file__).parent / "data"


def load_models(model_dir=None):
    model_dir = Path(model_dir) if model_dir else DEFAULT_MODEL_DIR
    binary_path = model_dir / "binary_classifier.pkl"
    category_path = model_dir / "category_classifier.pkl"

    if not binary_path.exists() or not category_path.exists():
        print("Error: Models not found. Run train.py first.")
        sys.exit(1)

    with open(binary_path, "rb") as f:
        binary_model = pickle.load(f)
    with open(category_path, "rb") as f:
        category_model = pickle.load(f)

    return binary_model, category_model


def predict(texts, binary_model, category_model):
    """Predict PII status and category for a list of texts."""
    results = []

    binary_pred = binary_model.predict(texts)
    binary_proba = binary_model.predict_proba(texts)

    for i, text in enumerate(texts):
        is_pii = bool(binary_pred[i])
        confidence = float(binary_proba[i][binary_pred[i]])

        result = {
            "text": text,
            "is_pii": is_pii,
            "confidence": confidence,
            "category": None,
        }

        if is_pii:
            cat_pred = category_model.predict([text])[0]
            result["category"] = cat_pred

        results.append(result)

    return results


def evaluate_test_set(model_dir=None, data_dir=None):
    """Evaluate models on the held-out test set."""
    from sklearn.metrics import accuracy_score, classification_report, f1_score

    binary_model, category_model = load_models(model_dir)

    data_dir = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
    test_path = data_dir / "test.csv"
    if not test_path.exists():
        print("Error: test.csv not found. Run generate_data.py first.")
        sys.exit(1)

    texts, labels, categories = [], [], []
    with open(test_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            texts.append(row["text"])
            labels.append(int(row["label"]))
            categories.append(row["category"])

    labels = np.array(labels)

    print("=" * 60)
    print("TEST SET EVALUATION")
    print("=" * 60)
    print(f"Samples: {len(texts)} (PII: {sum(labels)}, non-PII: {len(labels) - sum(labels)})")

    # Binary evaluation
    binary_pred = binary_model.predict(texts)
    acc = accuracy_score(labels, binary_pred)
    f1 = f1_score(labels, binary_pred)
    print(f"\nBinary Detection:")
    print(f"  Accuracy: {acc:.4f}")
    print(f"  F1 Score: {f1:.4f}")
    print(classification_report(labels, binary_pred, target_names=["non-PII", "PII"]))

    # Category evaluation (PII only)
    pii_texts = [t for t, l in zip(texts, labels) if l == 1]
    pii_cats = [c for c, l in zip(categories, labels) if l == 1]

    if pii_texts:
        cat_pred = category_model.predict(pii_texts)
        cat_acc = accuracy_score(pii_cats, cat_pred)
        cat_f1 = f1_score(pii_cats, cat_pred, average="weighted", zero_division=0)
        print(f"Category Classification (PII only):")
        print(f"  Accuracy:      {cat_acc:.4f}")
        print(f"  F1 (weighted): {cat_f1:.4f}")
        print(classification_report(pii_cats, cat_pred, zero_division=0))


def interactive(model_dir=None):
    """Interactive prediction mode."""
    binary_model, category_model = load_models(model_dir)

    print("PII Detection - Interactive Mode")
    print("Type text to analyze, 'quit' to exit.\n")

    while True:
        try:
            text = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if text.lower() in ("quit", "exit", "q"):
            break
        if not text:
            continue

        results = predict([text], binary_model, category_model)
        r = results[0]

        if r["is_pii"]:
            print(f"  PII DETECTED  (confidence: {r['confidence']:.2%}, category: {r['category']})")
        else:
            print(f"  Not PII       (confidence: {r['confidence']:.2%})")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="PII detection inference")
    parser.add_argument("--model_dir", type=str, default=None,
                        help="Directory containing trained models (default: ml/models/)")
    parser.add_argument("--data_dir", type=str, default=None,
                        help="Directory containing test.csv (default: ml/data/)")
    parser.add_argument("--test", action="store_true", help="Evaluate on test set")
    parser.add_argument("--interactive", action="store_true", help="Interactive mode")
    parser.add_argument("texts", nargs="*", help="Text(s) to predict")
    cli_args = parser.parse_args()

    if cli_args.test:
        evaluate_test_set(cli_args.model_dir, cli_args.data_dir)
    elif cli_args.interactive:
        interactive(cli_args.model_dir)
    elif cli_args.texts:
        binary_model, category_model = load_models(cli_args.model_dir)
        results = predict(cli_args.texts, binary_model, category_model)
        for r in results:
            status = "PII" if r["is_pii"] else "non-PII"
            cat = f" [{r['category']}]" if r["category"] else ""
            print(f"  {r['text']:<40s}  {status}{cat}  ({r['confidence']:.2%})")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
