# When to Use Cohere

Decision guide for choosing Cohere vs other providers for specific agent workloads.

## Strong fits for Cohere

### 1. RAG systems with strict citation requirements

Enterprise buyers in legal, finance, healthcare, and research domains often require answers to explicitly reference source documents. Cohere's native `documents=` + `citations` response is the cleanest implementation available.

Without Cohere, citation systems typically require:
- Custom prompt engineering to request citations.
- Parsing citations out of natural-language output.
- Matching parsed citations back to source IDs.
- Handling partial or fabricated citations.

With Cohere, you get structured, span-level citations with source IDs for free.

### 2. Multilingual retrieval

Cohere Embed v3 multilingual supports 100+ languages with consistent embedding quality. Use cases:
- Global customer-support knowledge bases.
- Cross-language document search.
- Multilingual corpus retrieval.

Competitors: OpenAI text-embedding-3-large is competitive but not multilingual-first. Google text-embedding-004 is solid on major languages. Cohere tends to win on broader language coverage.

### 3. Two-stage retrieval with Rerank

Cohere Rerank is a neural reranker that materially improves retrieval quality. Common pattern:

1. First-stage: embedding search (any provider) → top-50 candidates.
2. Second-stage: Cohere Rerank → top-5.
3. Generation: any LLM with top-5 as context.

Rerank improves retrieval quality even when you're not using Cohere for generation. Many teams use Cohere specifically for Rerank.

### 4. Cost-sensitive production workloads

Command R+: $2.50 input / $10 output per 1M tokens (vs Claude Sonnet $3/$15, GPT-4o $2.50/$10). Command R: $0.15/$0.60 — much cheaper than Haiku-tier from other providers. Command R7B even cheaper.

For high-volume production, Cohere's cost curve is often the most favorable.

### 5. Enterprise deployment with on-prem / airgap requirement

Cohere Toolkit provides a deployable artifact customers can run in their own infrastructure, including airgap environments. This is competitive differentiation vs API-only providers (Anthropic, OpenAI) for regulated-industry customers.

## Reasonable fits (consider alternatives)

### Agent orchestration

Cohere's tool-use API is solid but not distinctive. If your primary workload is multi-step agentic workflows, Claude Sonnet or GPT-4o are equally good choices. stage-pilot works equally well with any of them.

### Conversational assistants

Cohere Command is fine, but Claude Sonnet tends to produce more natural conversation and handle long conversations with more consistency.

### Coding assistants

GPT-4o and Claude Sonnet have more training on code and are generally preferred for developer tools.

## Weak fits

### Complex reasoning

For puzzle solving, mathematical reasoning, or multi-step planning requiring deep thought, Claude Sonnet with extended thinking or GPT-o3 will outperform Command.

### Vision

Cohere doesn't have a native vision model with the depth of GPT-4o or Claude. Use Claude or GPT for vision; use Cohere for text processing after vision extraction.

### Latency-critical sub-second flows

For sub-second response requirements (autocomplete, suggestion UI), smaller models from Anthropic (Haiku) or OpenAI (GPT-4o-mini) have similar or better latency characteristics.

## Mixed / hybrid patterns

### Pattern: Cohere Rerank + Claude Sonnet generation

Very common. Cohere's Rerank for retrieval quality; Claude's generation for reasoning quality. Cost: Rerank is ~$2/1K queries; Claude generation scales with input tokens.

### Pattern: Cohere Command for RAG; Claude for agents

Some teams route workloads: RAG queries to Command (for citation rendering); agentic workflows to Claude (for tool-use reliability). Requires routing logic but optimizes each task.

### Pattern: Cohere Embed + Pinecone + Cohere Command

Pure-Cohere stack for companies standardizing on Cohere. Pros: single vendor, simplified procurement. Cons: vendor lock-in.

## Decision tree

```
Is RAG with strict citations the primary use case?
├── Yes → Cohere Command (strong fit)
└── No ↓

Is multilingual retrieval / embedding critical?
├── Yes → Cohere Embed v3 (strong fit for embedding, can mix with other generation)
└── No ↓

Is the workload reasoning-heavy?
├── Yes → Claude Sonnet (extended thinking) or GPT-o3
└── No ↓

Is cost per token the dominant concern at scale?
├── Yes → Evaluate Command R/R7B vs Haiku/GPT-4o-mini
└── No ↓

Is on-prem / airgap deployment required?
├── Yes → Cohere Toolkit (strong fit) or self-hosted open-weights
└── No ↓

Default: pick based on team familiarity, any provider works for most workloads.
```

## Migration cost considerations

If you already have a Claude or OpenAI codebase, migrating to Cohere costs:

- **Code**: 1-3 days to swap SDK calls (see docs/migration-from-claude.md).
- **Prompts**: expect 2-5 prompt revisions per flow; Cohere responds differently to identical prompts.
- **Eval suite**: re-run; record baseline.
- **Cost model**: rebuild; different pricing.
- **Operational tooling**: depending on your observability stack, minor changes.

Total: 1-2 weeks for a mid-size app. Don't undertake unless the business case is strong.

## Operational maturity comparison (April 2026)

| Aspect | Cohere | Anthropic | OpenAI |
|--------|--------|-----------|--------|
| API stability | Good (v2 current) | Good | Good |
| Rate limits (enterprise tier) | Good | Good | Good |
| Enterprise contract / MSA | Yes | Yes | Yes |
| HIPAA BAA | Yes | Yes | Yes |
| SOC 2 Type II | Yes | Yes | Yes |
| Private deployment option | Yes (Toolkit) | Limited (AWS Bedrock) | Limited (Azure OpenAI) |
| Regional availability | Good | Good (US/EU) | Good |
| Documentation quality | Good | Very good | Very good |
| SDK quality | Good | Very good | Very good |
| Community content | Growing | Large | Largest |

## Final recommendation framework

1. **Build a 1-day prototype in Cohere** alongside your primary provider choice.
2. **Run on your actual task** (not a synthetic benchmark).
3. **Measure**: quality, cost, latency, citation reliability.
4. **Pick on measurement**, not marketing.

No decision here should be based on a vendor pitch. Always prototype.
