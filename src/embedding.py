# -*- coding: utf-8 -*-

"""
RAG V5.1
BGE-M3 Embedding
"""

from typing import List

import numpy as np
from sentence_transformers import SentenceTransformer

from .config import EMBEDDING_MODEL


_model = None


def get_model():

    global _model

    if _model is None:

        print(
            f"加载 Embedding 模型：{EMBEDDING_MODEL}"
        )

        _model = SentenceTransformer(
            EMBEDDING_MODEL
        )

        print("Embedding 模型加载完成")

    return _model


def embed_text(
    text: str,
) -> List[float]:

    if not text:
        raise ValueError(
            "embed_text() 收到空文本"
        )

    model = get_model()

    vector = model.encode(
        text,
        normalize_embeddings=True,
    )

    return vector.tolist()


def embed_texts(
    texts: List[str],
) -> List[List[float]]:

    if not texts:

        return []

    model = get_model()

    vectors = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=True,
    )

    return vectors.tolist()