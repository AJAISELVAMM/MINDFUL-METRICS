"""Compact semantic embeddings.

If sentence-transformers (all-MiniLM-L6-v2) is installed it is used.
Otherwise TF-IDF n-grams + TruncatedSVD (32-d) — a compact semantic
representation suitable for small academic datasets.
The encoder is fitted once on the communication corpus and reused.
"""
from __future__ import annotations

import os
from typing import Iterable

import joblib
import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer

N_COMPONENTS = 32


class SemanticEncoder:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1, max_features=4000, lowercase=True)
        self.svd = TruncatedSVD(n_components=N_COMPONENTS, random_state=42)
        self.backend = "tfidf_svd"
        self._st = None

    def fit(self, texts: Iterable[str]):
        texts = [t or "" for t in texts]
        x = self.vectorizer.fit_transform(texts)
        k = min(N_COMPONENTS, max(2, x.shape[1] - 1), x.shape[0] - 1)
        self.svd.n_components = k
        self.svd.fit(x)
        try:
            from sentence_transformers import SentenceTransformer  # noqa: F401
            self._st = SentenceTransformer("all-MiniLM-L6-v2")
            self.backend = "all-MiniLM-L6-v2"
        except Exception:
            self._st = None
            self.backend = "tfidf_svd"
        return self

    def encode(self, texts: Iterable[str]) -> np.ndarray:
        texts = [t or "" for t in texts]
        if self._st is not None:
            return np.asarray(self._st.encode(texts, show_progress_bar=False))
        x = self.vectorizer.transform(texts)
        return self.svd.transform(x)

    def derived_features(self, texts: Iterable[str]) -> np.ndarray:
        """Mean, std, l2-norm of embedding — compact features for RF."""
        emb = self.encode(texts)
        mean = emb.mean(axis=1, keepdims=True)
        std = emb.std(axis=1, keepdims=True)
        nrm = np.linalg.norm(emb, axis=1, keepdims=True)
        return np.hstack([mean, std, nrm, emb[:, :8] if emb.shape[1] >= 8 else emb])


def load_encoder(path: str) -> SemanticEncoder:
    return joblib.load(path)
