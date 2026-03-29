#!/usr/bin/env python3
"""
Training Pipeline for PII Detection Models

Trains two models:
1. Binary classifier: detects whether text contains PII (label 0/1)
2. Category classifier: classifies PII into categories (ssn, email, phone, etc.)

Evaluates on validation set, reports metrics, and saves models.
"""

import csv
import json
import os
import pickle
import sys
from pathlib import Path

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

from model import build_binary_classifier, build_category_classifier

DEFAULT_DATA_DIR = Path(__file__).parent / "data"
DEFAULT_MODEL_DIR = Path(__file__).parent / "models"


def load_dataset(path):
    """Load a CSV dataset and return texts, binary labels, and categories."""
    texts, labels, categories = [], [], []
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            texts.append(row["text"])
            labels.append(int(row["label"]))
            categories.append(row["category"])
    return texts, np.array(labels), categories


def train_binary(train_texts, train_labels, val_texts, val_labels):
    """Train and evaluate the binary PII detector."""
    print("=" * 60)
    print("BINARY PII DETECTION MODEL")
    print("=" * 60)

    model = build_binary_classifier()

    print("Training...")
    model.fit(train_texts, train_labels)

    print("Evaluating on validation set...")
    val_pred = model.predict(val_texts)

    acc = accuracy_score(val_labels, val_pred)
    prec = precision_score(val_labels, val_pred)
    rec = recall_score(val_labels, val_pred)
    f1 = f1_score(val_labels, val_pred)

    print(f"\n  Accuracy:  {acc:.4f}")
    print(f"  Precision: {prec:.4f}")
    print(f"  Recall:    {rec:.4f}")
    print(f"  F1 Score:  {f1:.4f}")

    print("\nClassification Report:")
    print(classification_report(val_labels, val_pred,
                                target_names=["non-PII", "PII"]))

    cm = confusion_matrix(val_labels, val_pred)
    print("Confusion Matrix:")
    print(f"  {'':>10s} pred:non-PII  pred:PII")
    print(f"  {'true:non-PII':>14s}  {cm[0][0]:>8d}  {cm[0][1]:>8d}")
    print(f"  {'true:PII':>14s}  {cm[1][0]:>8d}  {cm[1][1]:>8d}")

    metrics = {
        "accuracy": float(acc),
        "precision": float(prec),
        "recall": float(rec),
        "f1": float(f1),
    }
    return model, metrics


def train_category(train_texts, train_categories, val_texts, val_categories,
                   train_labels, val_labels):
    """Train and evaluate the PII category classifier (PII samples only)."""
    print("\n" + "=" * 60)
    print("PII CATEGORY CLASSIFICATION MODEL")
    print("=" * 60)

    # Filter to PII-only samples
    train_pii_texts = [t for t, l in zip(train_texts, train_labels) if l == 1]
    train_pii_cats = [c for c, l in zip(train_categories, train_labels) if l == 1]
    val_pii_texts = [t for t, l in zip(val_texts, val_labels) if l == 1]
    val_pii_cats = [c for c, l in zip(val_categories, val_labels) if l == 1]

    print(f"Training on {len(train_pii_texts)} PII samples...")
    print(f"Validating on {len(val_pii_texts)} PII samples...")

    unique_cats = sorted(set(train_pii_cats))
    print(f"Categories ({len(unique_cats)}): {unique_cats}")

    model = build_category_classifier()
    model.fit(train_pii_texts, train_pii_cats)

    print("\nEvaluating on validation set...")
    val_pred = model.predict(val_pii_texts)

    acc = accuracy_score(val_pii_cats, val_pred)
    f1_macro = f1_score(val_pii_cats, val_pred, average="macro", zero_division=0)
    f1_weighted = f1_score(val_pii_cats, val_pred, average="weighted", zero_division=0)

    print(f"\n  Accuracy:    {acc:.4f}")
    print(f"  F1 (macro):  {f1_macro:.4f}")
    print(f"  F1 (weighted): {f1_weighted:.4f}")

    print("\nPer-Category Report:")
    print(classification_report(val_pii_cats, val_pred, zero_division=0))

    metrics = {
        "accuracy": float(acc),
        "f1_macro": float(f1_macro),
        "f1_weighted": float(f1_weighted),
        "categories": unique_cats,
    }
    return model, metrics


def save_model(model, path):
    with open(path, "wb") as f:
        pickle.dump(model, f)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Train PII detection ML models")
    parser.add_argument("--data_dir", type=str, default=None,
                        help="Directory containing train.csv and val.csv (default: ml/data/)")
    parser.add_argument("--model_dir", type=str, default=None,
                        help="Directory to save trained models (default: ml/models/)")
    cli_args = parser.parse_args()

    data_dir = Path(cli_args.data_dir) if cli_args.data_dir else DEFAULT_DATA_DIR
    model_dir = Path(cli_args.model_dir) if cli_args.model_dir else DEFAULT_MODEL_DIR

    # Load datasets
    print("Loading datasets...")
    train_texts, train_labels, train_cats = load_dataset(data_dir / "train.csv")
    val_texts, val_labels, val_cats = load_dataset(data_dir / "val.csv")

    print(f"  Train: {len(train_texts)} samples "
          f"(PII: {sum(train_labels)}, non-PII: {len(train_labels) - sum(train_labels)})")
    print(f"  Val:   {len(val_texts)} samples "
          f"(PII: {sum(val_labels)}, non-PII: {len(val_labels) - sum(val_labels)})")

    # Train binary model
    binary_model, binary_metrics = train_binary(
        train_texts, train_labels, val_texts, val_labels)

    # Train category model
    category_model, category_metrics = train_category(
        train_texts, train_cats, val_texts, val_cats, train_labels, val_labels)

    # Save models
    model_dir.mkdir(parents=True, exist_ok=True)
    save_model(binary_model, model_dir / "binary_classifier.pkl")
    save_model(category_model, model_dir / "category_classifier.pkl")

    # Save metrics
    all_metrics = {
        "binary": binary_metrics,
        "category": category_metrics,
    }
    with open(model_dir / "metrics.json", "w") as f:
        json.dump(all_metrics, f, indent=2)

    print(f"\nModels saved to {model_dir}/")
    print("  binary_classifier.pkl")
    print("  category_classifier.pkl")
    print("  metrics.json")


if __name__ == "__main__":
    main()
