# OBLITERATUS — Weight-Level Refusal Removal

Remove refusal behaviors from open-weight LLMs via mechanistic interpretability. AGPL-3.0 — invoke via CLI only, never import as Python library.

## Quick Start

```bash
obliteratus obliterate <model_name> --method advanced --output-dir ./abliterated-models
```

## Method Selection

| Method | When | Speed |
|--------|------|-------|
| `advanced` (default) | Most models — multi-direction SVD, norm-preserving | 10-20 min (8B) |
| `basic` | Quick test / prototyping | 5-10 min (8B) |
| `surgical` | Reasoning models (R1 distills) — preserves CoT | 1-2 hrs |
| `nuclear` | MoE models (Mixtral, DeepSeek-MoE) | Slow |
| `aggressive` | Stubborn refusals persist | Risk of damage |

## VRAM Requirements

| VRAM | Max Model Size |
|------|---------------|
| CPU only | ~1B |
| 4-8 GB | ~4B |
| 8-16 GB | ~9B |
| 24 GB | ~32B |
| 48 GB+ | ~72B+ |

## Verification

| Metric | Good | Warning |
|--------|------|---------|
| Refusal rate | < 5% | > 10% |
| Perplexity increase | < 10% | > 15% — coherence damaged |
| KL divergence | < 0.1 | > 0.5 — distribution shift |

## Pitfalls

- Models under ~1B respond poorly — fragmented refusal directions
- Always check perplexity — if > 15% increase, model is damaged
- MoE models need `nuclear` method
- Quantized models can't be re-quantized — abliterate full-precision, then quantize
- AGPL license — `import obliteratus` contaminates MIT projects
- `aggressive` can make things worse on small models

## Support Files

- `references/analysis-modules.md` — 28 analysis module reference
- `references/methods-guide.md` — Detailed CLI method reference
- `templates/abliteration-config.yaml` — Standard config template
