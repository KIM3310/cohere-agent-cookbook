# cohere-agent-cookbook

> Production-grade recipes for building agents on Cohere Command. Patterns for tool use, RAG, multi-agent coordination, and evaluation — designed for teams shipping Cohere-powered products.

[![CI](https://github.com/KIM3310/cohere-agent-cookbook/actions/workflows/ci.yml/badge.svg)](https://github.com/KIM3310/cohere-agent-cookbook/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![Cohere SDK](https://img.shields.io/badge/cohere-%3E%3D5.13-663399.svg)](https://github.com/cohere-ai/cohere-python)

---

## Why this exists

Cohere's Command models (Command R, Command R+, Command R7B) have distinct strengths for agentic workflows: native tool use, citation-grounded RAG, and first-class multi-step reasoning. This cookbook catalogs production patterns specifically designed around those strengths.

This is a sibling to [claude-agent-cookbook](https://github.com/KIM3310/claude-agent-cookbook) and [stage-pilot](https://github.com/KIM3310/stage-pilot). Every recipe here has a claude-cookbook equivalent; reading both teaches you the differences in how you'd design the same agent across ecosystems.

## The Recipes

| # | Recipe | Problem it solves | Cohere feature |
|---|--------|-------------------|----------------|
| 01 | [tool-use](recipes/01-tool-use/) | Single-turn tool calling | Native `tools=` parameter |
| 02 | [multi-step-tool-use](recipes/02-multi-step-tool-use/) | Agent chains tools to completion | Multi-turn with tool_results |
| 03 | [rag-with-citations](recipes/03-rag-with-citations/) | Ground answers in retrieved context with explicit citations | `documents=` parameter + citation rendering |
| 04 | [coral-conversation](recipes/04-coral-conversation/) | Long conversational context with Coral-style chat history | `chat_history=` parameter |
| 05 | [rerank-pipeline](recipes/05-rerank-pipeline/) | Two-stage retrieval: embedding + Cohere Rerank | Rerank API integration |
| 06 | [embed-multilingual](recipes/06-embed-multilingual/) | Cross-language semantic search | Embed v3 multilingual |
| 07 | [structured-output](recipes/07-structured-output/) | Get reliable structured JSON from Command | Pydantic validation + retry |
| 08 | [multi-agent-coordinator](recipes/08-multi-agent-coordinator/) | Coordinator + specialist pattern | Multi-message orchestration |
| 09 | [streaming-agents](recipes/09-streaming-agents/) | Streaming responses with tool-call interleaving | Stream + tool events |
| 10 | [eval-framework](recipes/10-eval-framework/) | Regression-test your Cohere prompts | Rubric-based eval, gold-set comparison |

## Quick Start

```bash
git clone https://github.com/KIM3310/cohere-agent-cookbook.git
cd cohere-agent-cookbook
make install

cp .env.example .env
# Set COHERE_API_KEY

make recipe NAME=01-tool-use
```

## The common/ layer

- **`common/client.py`** — Cohere client wrapper with retry, token counting, cost estimation.
- **`common/eval.py`** — Rubric-based evaluation framework (identical to claude cookbook for portability).
- **`common/tools.py`** — Pydantic tool definitions.
- **`common/types.py`** — Shared types for Cohere response shapes.
- **`common/logging.py`** — Structured logging.

## When to use Cohere vs Claude vs GPT

Quick heuristic:

| Need | Best fit |
|------|----------|
| Citation-grounded RAG with explicit source attribution | **Cohere Command** (citation rendering is native) |
| Multi-lingual retrieval and embedding | **Cohere Embed v3 multilingual** |
| Long reasoning / chain of thought | **Claude (extended thinking) or GPT-o3** |
| Vision | Claude or GPT-4o |
| Best tool-calling reliability | Claude Sonnet with stage-pilot layer |
| Enterprise self-hosting option | Cohere (Cohere Toolkit / private deployment) |

Details in [docs/when-to-use-cohere.md](docs/when-to-use-cohere.md).

## Migration from Claude/OpenAI

If your agent was built on Claude or OpenAI SDKs, most patterns translate cleanly. Key differences:

- Cohere's native citation rendering replaces your custom citation logic in RAG.
- Cohere's Rerank API is a first-class citizen; most teams use it even with non-Cohere generation.
- Tool use is simpler: no `tool_calls` vs `function_calls` SDK quirks.
- System prompts live in `preamble` field, not a separate `system` parameter.

See [docs/migration-from-claude.md](docs/migration-from-claude.md) for side-by-side examples.

## Production considerations

- Rate limits: Cohere production tier starts generous; check your tier.
- Cost: input $2.50/M, output $10/M for Command R+ (April 2026). Rerank billed separately.
- Self-hosting: Cohere Toolkit allows on-prem. See [docs/self-hosting.md](docs/self-hosting.md).

## Related Projects

| Project | Relationship |
|---------|-------------|
| [claude-agent-cookbook](https://github.com/KIM3310/claude-agent-cookbook) | Claude-specific version of this cookbook |
| [stage-pilot](https://github.com/KIM3310/stage-pilot) | Tool-call reliability runtime; works with Cohere via provider interface |
| [agent-orchestration-benchmark](https://github.com/KIM3310/agent-orchestration-benchmark) | Benchmark suite comparing agent frameworks (Cohere included) |
| [AegisOps](https://github.com/KIM3310/AegisOps) | Multimodal incident analysis; uses Cohere Rerank for retrieval |
| [fde-engagement-playbook](https://github.com/KIM3310/fde-engagement-playbook) | Field playbook for FDE-style enterprise engagements |

## License

MIT. Contributions welcome via PR.

## Cloud + AI Architecture

This repository includes a neutral cloud and AI engineering blueprint that maps the current proof surface to runtime boundaries, data contracts, model-risk controls, deployment posture, and validation hooks.

- [Cloud + AI architecture blueprint](docs/cloud-ai-architecture.md)
- [Machine-readable architecture manifest](docs/architecture/blueprint.json)
- Validation command: `python3 scripts/validate_architecture_blueprint.py`
