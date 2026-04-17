"""Recipe 05 — Two-stage retrieval with Cohere Rerank.

Problem: First-stage embedding retrieval surfaces many candidates including
some irrelevant ones. Cohere Rerank acts as a second-stage filter, reordering
candidates by relevance to the query. Combining both gives higher-quality RAG.

Pipeline:
    Query → Embed → Vector DB (top-50) → Cohere Rerank (top-5) → Command LLM

Usage:
    python -m recipes.05-rerank-pipeline.recipe --query "..."
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from common.client import CookbookClient, SendResult  # noqa: E402


def rerank_documents(
    query: str,
    documents: list[dict],
    top_n: int = 5,
    model: str = "rerank-english-v3.0",
) -> list[dict]:
    """Call Cohere Rerank and return top-N documents by relevance.

    Each returned document has: {original_doc..., 'relevance_score': float}.
    """
    try:
        import cohere  # type: ignore
    except ImportError as e:
        raise RuntimeError("cohere package required") from e

    api_key = os.getenv("COHERE_API_KEY")
    if not api_key:
        raise RuntimeError("Set COHERE_API_KEY")

    client = cohere.ClientV2(api_key=api_key)

    # Cohere Rerank v2 API: documents can be dicts; specify rank_fields to control
    # which field(s) to rank on.
    doc_texts = [d.get("snippet", d.get("text", str(d))) for d in documents]

    response = client.rerank(
        model=model,
        query=query,
        documents=doc_texts,
        top_n=top_n,
    )

    # Map back to original documents
    results = []
    for item in response.results:
        original = documents[item.index]
        results.append(
            {
                **original,
                "relevance_score": item.relevance_score,
                "rank": len(results) + 1,
            }
        )
    return results


def run(query: str, corpus: list[dict] | None = None, top_n: int = 5) -> SendResult:
    """Run the full two-stage pipeline on a corpus."""
    if corpus is None:
        # Use the same sample corpus as recipe 03 (or extend)
        from recipes.__init__ import SAMPLE_CORPUS_EXTENDED as corpus  # type: ignore

    # Stage 1: (in production) embedding-based retrieval would go here,
    # typically producing top-50 candidates. For demonstration, we assume
    # the corpus is already the first-stage output.

    # Stage 2: Cohere Rerank
    top_docs = rerank_documents(query, corpus, top_n=top_n)

    # Stage 3: Command LLM with reranked docs
    client = CookbookClient()
    result = client.send(
        message=query,
        documents=[
            {
                "id": d.get("id", f"doc_{i}"),
                "title": d.get("title", "Untitled"),
                "snippet": d.get("snippet", ""),
            }
            for i, d in enumerate(top_docs)
        ],
        preamble=(
            "You are a helpful assistant. The provided documents have been reranked by "
            "relevance. Use them to answer the query. Cite your sources."
        ),
    )

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Recipe 05: Rerank pipeline")
    parser.add_argument("--query", required=True)
    parser.add_argument("--top-n", type=int, default=5)
    args = parser.parse_args()

    result = run(args.query, top_n=args.top_n)
    print(f"Answer: {result.text}")
    print(f"\nTokens: in={result.input_tokens}, out={result.output_tokens}")
    print(f"Cost:   ${result.cost_usd:.6f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
