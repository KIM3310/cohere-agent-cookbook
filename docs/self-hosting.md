# Self-Hosting Cohere

Practical guide for deploying Cohere models in private / airgapped environments using Cohere Toolkit and licensed model weights.

## Before you start

### Prerequisites

- Licensed model weights from Cohere (enterprise contract required).
- Hardware: NVIDIA GPUs (A100 or H100 recommended for Command R+; A10G sufficient for smaller variants).
- Kubernetes cluster (1.28+) or bare-metal with GPU drivers.
- 100+ GB disk for model weights + artifact storage.

### Why self-host

- Data sovereignty / airgap requirements.
- Regulatory constraints preventing third-party API calls.
- Very high volume where API billing exceeds hardware TCO.
- Latency requirements (local inference eliminates round-trip).

### Why NOT self-host

- You don't have GPU infrastructure expertise.
- Volume doesn't justify it (< 50M tokens/month, API is cheaper).
- You need frequent model updates (Cohere manages updates centrally).
- Your use case is prototype / research.

## Deployment options

### Option 1: Cohere Toolkit (Docker / Kubernetes)

Cohere's official deployment stack. Runs on standard K8s.

Architecture:
```
┌─────────────────────────────┐
│       Client Applications    │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│   Toolkit API Gateway        │ ← authenticates, routes, rate-limits
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│   Inference Service          │ ← model weights + inference runtime
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│   Vector DB (Qdrant / etc)   │ ← for RAG
└─────────────────────────────┘
```

### Option 2: Hugging Face TGI or vLLM

If your contract includes open-weight variants, you can run them via:

- **Text Generation Inference (TGI)**: Hugging Face's production inference server.
- **vLLM**: higher-throughput, OSS, widely adopted.

Pros: more control, better community tooling.
Cons: not official Cohere deployment; features (Rerank, multi-step agent) require additional infrastructure.

## Sizing for Command R+ (104B params)

| Deployment | GPUs | RAM | Storage | Throughput (tok/s) |
|------------|------|-----|---------|--------------------|
| Single A100 80GB | 1 | 64GB | 250GB | ~200-400 |
| 2x A100 80GB | 2 | 128GB | 250GB | ~400-800 |
| 4x A100 80GB | 4 | 256GB | 250GB | ~800-1500 |
| Single H100 80GB | 1 | 64GB | 250GB | ~400-800 |
| 2x H100 80GB | 2 | 128GB | 250GB | ~800-1600 |

For Command R (35B), requirements scale down roughly 3x.

## Airgap-specific considerations

See [llm-onprem-deployment-kit](https://github.com/KIM3310/llm-onprem-deployment-kit) for a comprehensive airgap deployment pattern. Key points for Cohere specifically:

1. **Model weight distribution**: Cohere weights are large (100GB+). Use physical media or dedicated transfer session; not a casual download.
2. **License enforcement**: verify license mechanism works offline. Some setups require periodic license validation.
3. **Image mirror**: mirror Cohere Toolkit images to your private registry (skopeo).
4. **Dependency mirror**: Python deps, base images, runtime libraries all mirrored.
5. **Update cadence**: plan monthly or quarterly updates; build the process into operations.

## Observability

Self-hosted Cohere needs:

- **GPU metrics**: utilization, memory, temperature.
- **Inference metrics**: requests/sec, tokens/sec, latency p50/p95/p99.
- **Model metrics**: token throughput, cache hit rate.
- **Error metrics**: OOM, timeout, CUDA errors.

Standard Prometheus + Grafana stack covers this. DCGM exporter for GPU metrics.

## Operational cost model (self-hosted)

Rough cost for 2x A100 80GB on AWS (on-demand):

- Instance (p4d.24xlarge): $32.77/hour = ~$23K/month
- With reserved 1-year: ~$14K/month
- Storage: $200-500/month
- Network: $500-1500/month
- **Total**: $15-25K/month for the inference tier alone

Breakeven vs API: around 150-300M tokens/month at Command R+ API pricing. Below that threshold, the API is cheaper when you account for engineering ops time.

## Common self-hosting pitfalls

1. **Under-provisioning GPU memory**: models need activation memory beyond weights. Allow 30-50% headroom.
2. **Skipping the CUDA driver match**: Cohere's container requires specific CUDA versions. Double-check.
3. **No fallback**: when self-hosted goes down, nothing serves. Plan for API fallback or second region.
4. **Forgetting about model updates**: Cohere iterates; your self-host snapshot ages. Plan updates.
5. **Licensing audit panic**: keep clear records of license terms, usage, contracted model versions.

## Integration with cohere-agent-cookbook

Recipes in this cookbook work with Cohere's managed API by default. For self-hosted:

```python
# In common/client.py, point to self-hosted endpoint
client = cohere.ClientV2(
    api_key="your-license-token",
    base_url="https://cohere.internal.company.com/v1",
)
```

All recipes work unchanged.

## When to go back to managed

- Volume declines below breakeven.
- Team responsible for operating it leaves.
- Model version support requires features your self-host lacks.
- Operational incidents exceed what the savings justify.

## References

- [Cohere Toolkit](https://github.com/cohere-ai/cohere-toolkit) — official deployment stack.
- [llm-onprem-deployment-kit](https://github.com/KIM3310/llm-onprem-deployment-kit) — general on-prem LLM deployment patterns.
- [fde-engagement-playbook](https://github.com/KIM3310/fde-engagement-playbook) — FDE playbook for customer deployments.
