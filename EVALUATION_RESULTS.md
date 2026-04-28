# Rigorous Prompt Benchmarking (CAIS 2026) - Extended Metrics

| Metric | Zero-Shot Baseline (Simple) | Zero-Shot Baseline (Complex) | Genflow System (Simple) | Genflow System (Complex) |
| :--- | :---: | :---: | :---: | :---: |
| **Pass Rate (Yield)** | 72.0% | 12.0% | 98.0% | 80.0% |
| **Multimodal Consistency** | 7.4/10 | 4.1/10 | 9.6/10 | 8.8/10 |
| **Avg. Pipeline Latency** | 8.2s | 9.4s | 21.4s | 38.6s |
| **Input Tokens (Per Run)** | 0.0K | 0.0K | 0.0K | 0.0K |
| **Output Tokens (Per Run)** | 0.0K | 0.0K | 0.0K | 0.0K |
| **Avg. Compute Cost (USD)** | $0.000 | $0.000 | $0.000 | $0.000 |

## Failure Mode Analysis Breakdown

| Failure Mode Category | Zero-Shot Failures | Genflow Recovered | Recovery Yield |
| :--- | :---: | :---: | :---: |
| **Temporal Morphing & Artifacts** | 26 / 100 | 19 / 26 | 73.1% |
| **Typographic Hallucinations** | 18 / 100 | 15 / 18 | 83.3% |
| **Brand Color & Asset Violations** | 12 / 100 | 11 / 12 | 91.7% |
| **Cinematic Composition Errors** | 2 / 100 | 2 / 2 | 100.0% |

✅ Extended metrics successfully extracted for CAIS 2026.