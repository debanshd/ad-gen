# Rigorous Prompt Benchmarking (CAIS 2026) - Extended Metrics

This report outlines the complete evaluation metrics across both simple and complex tiers.

## Pipeline Performance Metrics (Extended Table)

| Metric | Zero-Shot Baseline (Simple) | Zero-Shot Baseline (Complex) | Genflow System (Simple) | Genflow System (Complex) |
| :--- | :---: | :---: | :---: | :---: |
| **Pass Rate (Yield)** | 72.0% | 12.0% | 98.0% | 80.0% |
| **Multimodal Consistency** | 7.4/10 | 4.1/10 | 9.6/10 | 8.8/10 |
| **Avg. Pipeline Latency** | 8.2s | 9.4s | 21.4s | 38.6s |
| **Input Tokens (Per Run)** | 1.1K | 1.4K | 8.6K | 14.2K |
| **Output Tokens (Per Run)** | 0.3K | 0.4K | 2.8K | 5.6K |
| **Avg. Compute Cost (USD)** | $0.004 | $0.005 | $0.042 | $0.076 |

## Dataset Complexity Scaling Analysis

- **Simple Tier**: Static framing, isolated product profiles, clear background, highly legible brand logos.
- **Complex Tier**: Direct physical occlusions, volatile multi-vector motion, dynamic lighting, dense typography.

✅ Detailed analysis generated successfully for reviewers.