# Migration from Claude to Cohere

Side-by-side patterns for teams moving agent code from Claude/Anthropic SDK to Cohere Command.

## Idiom differences to know upfront

1. **System prompts go in `preamble`**, not `system`.
2. **Tool schema uses OpenAI-compatible `function` wrapper** (not Claude's flat tool object).
3. **Tool results are `role: "tool"` with JSON string content** (similar to OpenAI, different from Claude's nested tool_result content blocks).
4. **Citations are native via `documents=`** — you don't construct citation logic yourself.
5. **Rerank is a first-class companion API** — use it even if your generation is non-Cohere.
6. **`max_tokens` is required** (same as Claude; different from OpenAI default).

## Side-by-side: simple chat

**Claude:**
```python
client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    system="You are helpful.",
    messages=[{"role": "user", "content": "Hello"}],
)
```

**Cohere:**
```python
client.chat(
    model="command-r-plus-08-2024",
    messages=[
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Hello"},
    ],
    max_tokens=1024,
)
```

## Tool use

**Claude:**
```python
tools = [{
    "name": "get_weather",
    "description": "...",
    "input_schema": {
        "type": "object",
        "properties": {"city": {"type": "string"}},
        "required": ["city"],
    },
}]

response = client.messages.create(model=..., tools=tools, messages=[...])

for block in response.content:
    if block.type == "tool_use":
        tool_input = block.input  # dict
```

**Cohere:**
```python
tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "...",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"],
        },
    },
}]

response = client.chat(model=..., tools=tools, messages=[...])

if response.message.tool_calls:
    for tc in response.message.tool_calls:
        tool_name = tc.function.name
        tool_args = json.loads(tc.function.arguments)  # JSON string → dict
```

## Tool results

**Claude:**
```python
messages.append({"role": "assistant", "content": response.content})
messages.append({
    "role": "user",
    "content": [{
        "type": "tool_result",
        "tool_use_id": block.id,
        "content": json.dumps(result),
    }],
})
```

**Cohere:**
```python
messages.append({
    "role": "assistant",
    "content": response.message.content or "",
    "tool_calls": response.message.tool_calls,
})
messages.append({
    "role": "tool",
    "tool_call_id": tc.id,
    "content": json.dumps(result),
})
```

## RAG with citations — Cohere's distinctive feature

**Claude (manual citation):**
```python
# You build prompts that include the documents
documents_text = "\n".join(f"[{d['id']}]: {d['text']}" for d in docs)
prompt = f"Based on these documents:\n{documents_text}\n\nAnswer: {query}"
response = client.messages.create(model=..., messages=[{"role": "user", "content": prompt}])
# Parse citations out of response text manually (fragile)
```

**Cohere (native):**
```python
response = client.chat(
    model="command-r-plus-08-2024",
    messages=[{"role": "user", "content": query}],
    documents=[
        {"id": "doc_001", "title": "...", "snippet": "..."},
        {"id": "doc_002", "title": "...", "snippet": "..."},
    ],
)
# response.message.citations is a list of span-level citations
for c in response.message.citations:
    print(c.start, c.end, c.text, [s.id for s in c.sources])
```

Cohere's native citation rendering means your RAG output has reliable, machine-parseable source attribution. This is the main reason teams use Cohere for RAG even when generation quality is similar across providers.

## Rerank (Cohere-specific)

Even if you use a different LLM for generation, Cohere Rerank improves retrieval quality as a second stage:

```python
rerank_response = client.rerank(
    model="rerank-english-v3.0",
    query=query,
    documents=[d["text"] for d in candidates],  # from your embedding retrieval
    top_n=5,
)

# Keep top N reranked
reranked = [candidates[r.index] for r in rerank_response.results]
```

Use this whether or not you use Cohere for generation. Rerank is often the single biggest retrieval-quality improvement.

## Streaming

**Claude:**
```python
with client.messages.stream(model=..., messages=[...]) as stream:
    for text in stream.text_stream:
        print(text, end="")
    final = stream.get_final_message()
```

**Cohere:**
```python
stream = client.chat_stream(model=..., messages=[...])
for event in stream:
    if event.type == "content-delta":
        print(event.delta.message.content.text, end="")
    elif event.type == "tool-call-delta":
        # handle tool call streaming
        pass
    elif event.type == "message-end":
        # final complete message
        pass
```

## Pricing comparison (April 2026)

| Model | Input ($/M) | Output ($/M) |
|-------|-------------|-------------|
| Claude Sonnet 4 | 3.00 | 15.00 |
| Claude Haiku 4 | 0.25 | 1.25 |
| Cohere Command R+ | 2.50 | 10.00 |
| Cohere Command R | 0.15 | 0.60 |
| Cohere Command R7B | 0.0375 | 0.15 |

## When to pick Cohere over Claude

- **Primary RAG workload with strict citation requirements**: Cohere wins on citation UX.
- **Multilingual retrieval (100+ languages)**: Cohere Embed v3 multilingual is strong.
- **Cost-sensitive production at scale**: Command R / R7B are materially cheaper.
- **Self-hosting required**: Cohere Toolkit provides on-prem deployment path.

## When to stick with Claude

- **Complex reasoning tasks**: Claude Sonnet (esp. with extended thinking) tends to win.
- **Vision**: Claude has broader vision capabilities.
- **Long-context adherence (>100K tokens)**: Claude tends to hold context better in the long tail.

## Migration checklist

- [ ] Replace `system=` with `preamble` in your code.
- [ ] Rewrap tool schemas in `function` wrapper.
- [ ] Change tool-result role from `user`/`tool_result` block to `role: "tool"` with JSON content.
- [ ] Replace manual RAG citation logic with `documents=` + `response.message.citations`.
- [ ] Consider adding Rerank as a retrieval stage (independent of generation provider).
- [ ] Update cost model using Cohere pricing.
- [ ] Re-run eval suite; expect prompts may need tuning (models respond differently to identical prompts).
- [ ] Test streaming event handling (different event shape than Claude).
