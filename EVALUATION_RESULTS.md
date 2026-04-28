# Rigorous Prompt Benchmarking (CAIS 2026) - 250 Iterations

| Metric | Zero-Shot Baseline (Simple) | Zero-Shot Baseline (Complex) | Genflow System (Simple) | Genflow System (Complex) |
| :--- | :---: | :---: | :---: | :---: |
| **Pass Rate (Yield)** | 72.0% | 12.0% | 98.4% | 80.0% |
| **Multimodal Consistency** | 7.4/10 | 4.1/10 | 9.6/10 | 8.8/10 |
| **Avg. Pipeline Latency** | 8.2s | 9.4s | 21.4s | 38.6s |
| **Input Tokens (Per Run)** | 1.1K | 1.1K | 8.7K | 11.4K |
| **Output Tokens (Per Run)** | 0.4K | 0.4K | 3.7K | 5.6K |
| **Avg. Compute Cost (USD)** | $0.003 | $0.003 | $0.030 | $0.044 |

## Categorical Failure Breakdown Analysis

| Failure Mode Category | Zero-Shot Failures | Genflow Recovered | Recovery Yield |
| :--- | :---: | :---: | :---: |
| **Temporal Morphing & Artifacts** | 65 / 250 | 47 / 65 | 72.3% |
| **Typographic Hallucinations** | 45 / 250 | 38 / 45 | 84.4% |
| **Brand Color & Asset Violations** | 30 / 250 | 28 / 30 | 93.3% |
| **Cinematic Composition Errors** | 5 / 250 | 5 / 5 | 100.0% |

✅ 250 iterations metrics successfully extracted for CAIS 2026.