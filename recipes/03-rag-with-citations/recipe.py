"""Recipe 03 — RAG with Citations using Cohere Command.

Problem: Given a question and a set of documents, return an answer grounded
in the documents with explicit citations for each claim.

Cohere's distinctive feature here: the `documents=` parameter delivers
citation-attributable output out of the box, with span-level source
attribution rendered via `result.citations`.

Usage:
    python -m recipes.03-rag-with-citations.recipe --query "What is Cohere Rerank?"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from common.client import CookbookClient, SendResult  # noqa: E402


SAMPLE_DOCUMENTS = [
    {
        "id": "doc_001",
        "title": "Cohere Command Models",
        "snippet": (
            "Cohere Command R and Command R+ are large language models optimized "
            "for enterprise use cases including RAG, tool use, and agentic workflows. "
            "Command R+ is 104B parameters while Command R is 35B."
        ),
    },
    {
        "id": "doc_002",
        "title": "Cohere Rerank API",
        "snippet": (
            "Cohere Rerank is a neural reranker that reorders a list of documents "
            "based on relevance to a query. It improves retrieval quality in RAG systems "
            "by acting as a second-stage filter after initial embedding-based retrieval."
        ),
    },
    {
        "id": "doc_003",
        "title": "Cohere Embed v3",
        "snippet": (
            "Cohere Embed v3 is a multilingual embedding model supporting 100+ languages. "
            "It is available in standard and lightweight variants. The model produces "
            "1024-dimensional vectors optimized for retrieval tasks."
        ),
    },
    {
        "id": "doc_004",
        "title": "Deployment Options",
        "snippet": (
            "Cohere models can be accessed via the public API, on AWS Bedrock, Azure AI, "
            "Oracle Cloud, or via private deployment through Cohere Toolkit for on-prem "
            "and airgapped environments."
        ),
    },
]


def run(query: str, documents: list[dict] | None = None, model: str = "command-r-plus-08-2024") -> SendResult:
    """Run RAG query with citations."""
    if documents is None:
        documents = SAMPLE_DOCUMENTS

    client = CookbookClient(default_model=model)

    result = client.send(
        message=query,
        documents=documents,
        preamble=(
            "You are a helpful assistant. Answer the user's question based on the "
            "provided documents. Always cite your sources. If the documents don't "
            "contain enough information, say so explicitly."
        ),
        temperature=0.0,
    )

    return result


def format_cited_answer(result: SendResult) -> str:
    """Render the answer with inline citations."""
    if not result.citations:
        return result.text

    # Cohere citations are character-span-based
    text = result.text
    citations_by_end = sorted(result.citations, key=lambda c: c["end"], reverse=True)

    # Insert [n] markers after each cited span
    for i, c in enumerate(citations_by_end):
        end = c["end"]
        if end is not None and end <= len(text):
            marker_idx = len(citations_by_end) - i
            text = text[:end] + f"[{marker_idx}]" + text[end:]

    # Append source list
    text += "\n\nSources:"
    for i, c in enumerate(sorted(result.citations, key=lambda c: c["end"]), 1):
        source_ids = [s["id"] for s in c.get("sources", [])]
        text += f"\n[{i}] {', '.join(source_ids)}"

    return text


def main() -> int:
    parser = argparse.ArgumentParser(description="Recipe 03: RAG with citations")
    parser.add_argument("--query", required=True)
    parser.add_argument("--model", default="command-r-plus-08-2024")
    args = parser.parse_args()

    result = run(args.query, model=args.model)
    print(format_cited_answer(result))
    print("\n---")
    print(f"Tokens: in={result.input_tokens}, out={result.output_tokens}")
    print(f"Cost:   ${result.cost_usd:.6f}")
    print(f"Citations: {len(result.citations)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
