#!/usr/bin/env python3
"""
PII Detection ML Model

A text classification model that detects PII (Personally Identifiable Information)
in text strings. Uses TF-IDF features with character n-grams, combined with
handcrafted structural features for better pattern recognition.
"""

import re
import string

import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline, FeatureUnion


class StructuralFeatureExtractor(BaseEstimator, TransformerMixin):
    """Extract handcrafted structural features from text."""

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        features = []
        for text in X:
            features.append(self._extract(str(text)))
        return np.array(features)

    def _extract(self, text):
        length = len(text)
        digit_ratio = sum(c.isdigit() for c in text) / max(length, 1)
        alpha_ratio = sum(c.isalpha() for c in text) / max(length, 1)
        upper_ratio = sum(c.isupper() for c in text) / max(length, 1)
        special_ratio = sum(not c.isalnum() and not c.isspace() for c in text) / max(length, 1)
        space_ratio = sum(c.isspace() for c in text) / max(length, 1)

        has_at = 1.0 if "@" in text else 0.0
        has_dash = 1.0 if "-" in text else 0.0
        has_dot = 1.0 if "." in text else 0.0
        has_plus = 1.0 if "+" in text else 0.0
        has_colon = 1.0 if ":" in text else 0.0
        has_slash = 1.0 if "/" in text else 0.0
        has_paren = 1.0 if "(" in text or ")" in text else 0.0

        # Digit group patterns
        digit_groups = re.findall(r"\d+", text)
        num_digit_groups = len(digit_groups)
        max_digit_group_len = max((len(g) for g in digit_groups), default=0)
        avg_digit_group_len = np.mean([len(g) for g in digit_groups]) if digit_groups else 0.0

        # Separator patterns
        num_dashes = text.count("-")
        num_dots = text.count(".")
        num_spaces = text.count(" ")

        # Starts with specific patterns
        starts_digit = 1.0 if text and text[0].isdigit() else 0.0
        starts_alpha = 1.0 if text and text[0].isalpha() else 0.0
        starts_0x = 1.0 if text.startswith("0x") else 0.0
        starts_begin = 1.0 if text.startswith("-----BEGIN") else 0.0

        # Contains patterns
        has_country_prefix = 1.0 if re.match(r"^[A-Z]{2}\d", text) else 0.0
        has_http = 1.0 if text.startswith("http") else 0.0

        # Unicode detection (CJK characters)
        cjk_count = sum(1 for c in text if "\u4e00" <= c <= "\u9fff" or
                        "\u3040" <= c <= "\u309f" or "\u30a0" <= c <= "\u30ff" or
                        "\uac00" <= c <= "\ud7af")
        cjk_ratio = cjk_count / max(length, 1)

        # Entropy (character diversity)
        if length > 0:
            freq = {}
            for c in text:
                freq[c] = freq.get(c, 0) + 1
            entropy = -sum((v / length) * np.log2(v / length) for v in freq.values())
        else:
            entropy = 0.0

        return [
            length, digit_ratio, alpha_ratio, upper_ratio, special_ratio, space_ratio,
            has_at, has_dash, has_dot, has_plus, has_colon, has_slash, has_paren,
            num_digit_groups, max_digit_group_len, avg_digit_group_len,
            num_dashes, num_dots, num_spaces,
            starts_digit, starts_alpha, starts_0x, starts_begin,
            has_country_prefix, has_http,
            cjk_ratio, entropy,
        ]

    def get_feature_names_out(self):
        return [
            "length", "digit_ratio", "alpha_ratio", "upper_ratio", "special_ratio", "space_ratio",
            "has_at", "has_dash", "has_dot", "has_plus", "has_colon", "has_slash", "has_paren",
            "num_digit_groups", "max_digit_group_len", "avg_digit_group_len",
            "num_dashes", "num_dots", "num_spaces",
            "starts_digit", "starts_alpha", "starts_0x", "starts_begin",
            "has_country_prefix", "has_http",
            "cjk_ratio", "entropy",
        ]


def build_binary_classifier():
    """Build a pipeline for binary PII detection (is PII or not)."""
    return Pipeline([
        ("features", FeatureUnion([
            ("tfidf_char", TfidfVectorizer(
                analyzer="char_wb",
                ngram_range=(2, 5),
                max_features=5000,
                sublinear_tf=True,
            )),
            ("tfidf_word", TfidfVectorizer(
                analyzer="word",
                ngram_range=(1, 2),
                max_features=2000,
                sublinear_tf=True,
            )),
            ("structural", StructuralFeatureExtractor()),
        ])),
        ("classifier", LogisticRegression(
            C=1.0,
            max_iter=1000,
            class_weight="balanced",
            solver="lbfgs",
        )),
    ])


def build_category_classifier():
    """Build a pipeline for PII category classification."""
    return Pipeline([
        ("features", FeatureUnion([
            ("tfidf_char", TfidfVectorizer(
                analyzer="char_wb",
                ngram_range=(2, 5),
                max_features=5000,
                sublinear_tf=True,
            )),
            ("tfidf_word", TfidfVectorizer(
                analyzer="word",
                ngram_range=(1, 2),
                max_features=2000,
                sublinear_tf=True,
            )),
            ("structural", StructuralFeatureExtractor()),
        ])),
        ("classifier", GradientBoostingClassifier(
            n_estimators=200,
            max_depth=5,
            learning_rate=0.1,
            min_samples_split=5,
        )),
    ])
