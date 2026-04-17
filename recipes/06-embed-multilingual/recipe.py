"""Recipe 06 — Cross-language semantic search with Cohere Embed v3 multilingual.

Problem: Users in Korean, Japanese, and English need to search a single catalog.
Pattern: Embed documents once; embed query in any language; cosine similarity.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


SAMPLE_CATALOG = [
    {"id": "d1", "lang": "en", "text": "A romantic comedy set in a small Italian village."},
    {"id": "d2", "lang": "ko", "text": "한국의 작은 어촌 마을에서 펼쳐지는 가족 드라마."},
    {"id": "d3", "lang": "ja", "text": "東京の夜、ジャズバーで出会う二人の物語。"},
    {"id": "d4", "lang": "en", "text": "High-octane action thriller in the streets of Seoul."},
    {"id": "d5", "lang": "ko", "text": "서울 강남 한복판에서 펼쳐지는 첩보 액션."},
    {"id": "d6", "lang": "ja", "text": "京都の古い寺を舞台にした時代劇。"},
    {"id": "d7", "lang": "en", "text": "A historical drama set in a Kyoto temple."},
    {"id": "d8", "lang": "ko", "text": "가족의 유대를 그린 한국 드라마."},
]


def embed_documents(documents: list[dict], model: str = "embed-multilingual-v3.0") -> list[list[float]]:
    """Call Cohere Embed API on document text. Returns list of embeddings (1024-d)."""
    try:
        import cohere  # type: ignore
    except ImportError:
        raise RuntimeError("cohere package required") from None

    api_key = os.getenv("COHERE_API_KEY")
    if not api_key:
        raise RuntimeError("Set COHERE_API_KEY")

    client = cohere.ClientV2(api_key=api_key)

    texts = [d["text"] for d in documents]
    response = client.embed(
        model=model,
        input_type="search_document",
        texts=texts,
    )
    return response.embeddings.float_


def embed_query(text: str, model: str = "embed-multilingual-v3.0") -> list[float]:
    import cohere  # type: ignore

    client = cohere.ClientV2(api_key=os.getenv("COHERE_API_KEY"))
    response = client.embed(
        model=model,
        input_type="search_query",
        texts=[text],
    )
    return response.embeddings.float_[0]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    import math

    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    return dot / (norm_a * norm_b + 1e-10)


def search(query: str, catalog: list[dict], top_k: int = 5) -> list[dict]:
    query_vec = embed_query(query)
    doc_vecs = embed_documents(catalog)

    scored = []
    for doc, vec in zip(catalog, doc_vecs):
        score = cosine_similarity(query_vec, vec)
        scored.append({**doc, "score": score})

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True, help="Query in any language")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    results = search(args.query, SAMPLE_CATALOG, top_k=args.top_k)

    print(f"Query: {args.query}\n")
    print("Top matches:")
    for i, r in enumerate(results, 1):
        print(f"{i}. [{r['lang']}] score={r['score']:.3f} — {r['text']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
