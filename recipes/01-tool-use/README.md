# Recipe 01: Tool Use with Cohere Command

Single-turn tool invocation with one or more tools. Cohere Command natively supports `tools=` parameter; response returns `tool_calls` when the model decides to invoke.

## When to use

- User query requires data the model doesn't have (weather, time, database lookup).
- One tool call is sufficient to answer (not a chain).
- Deterministic tool invocation needed.

## When NOT to use

- Multi-step planning (use recipe 02).
- Retrieval over a knowledge base (use recipe 03 RAG).

## Pattern

```
User query
     │
     ▼
Cohere Command (with tools=)
     │
     ├─ Returns text only → answer immediately
     │
     └─ Returns tool_calls
         │
         ▼
      Execute tool locally
         │
         ▼
      Send tool_result back to Cohere
         │
         ▼
      Final answer
```

## Running

```bash
export COHERE_API_KEY=...
python -m recipes.01-tool-use.recipe --query "What's the weather in Seoul?"
```

Expected output:
```
Answer: The weather in Seoul is currently partly cloudy with a temperature of 18°C and humidity at 62%.

Tokens: in=183, out=42
Cost:   $0.000878
Latency: 742 ms
```

## Testing

```bash
pytest recipes/01-tool-use/test_recipe.py -v
```

Tests use a mocked Cohere client — no API key required in CI.

## Key implementation points

1. **Tool schema uses `function` wrapper**: Cohere v2 follows OpenAI-style tool definitions with a nested `function` object.
2. **Arguments come back as a JSON string**: parse with `json.loads()`.
3. **Tool results go back as `role: "tool"`**: include `tool_call_id` for correlation.
4. **Cohere may return text + tool_calls in one response**: check both fields.

## Differences from Claude and OpenAI

- Cohere uses `preamble` for system prompts (not `system`); this wrapper normalizes.
- Citations on tool-derived output are available via `result.citations` (Cohere distinctive feature).
- Tool result format uses `content` field as JSON string, similar to OpenAI.

## Extending

For production:
1. Replace mock `get_weather` with a real weather API call.
2. Add input validation on tool arguments via Pydantic (see `common/tools.py`).
3. Add rate limiting on tool execution.
4. Log every tool call for audit.
