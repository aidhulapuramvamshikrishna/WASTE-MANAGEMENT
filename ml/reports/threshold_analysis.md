# UI uncertainty threshold analysis (mobilenet_v3, validation set)

n = 2842 validation images, temperature T = 0.8392. Rule: lowest max-softmax threshold (0.005 grid, from 0.40) where accuracy of kept val predictions >= 97%.

| threshold | coverage | accuracy of kept | correct scans flagged | wrong scans caught |
|---|---|---|---|---|
| 0.400 | 96.1% | 94.47% | 50 | 62/213 (29%) |
| 0.450 | 94.4% | 95.04% | 79 | 80/213 (38%) |
| 0.500 | 92.2% | 95.84% | 118 | 104/213 (49%) |
| 0.550 | 90.3% | 96.53% | 152 | 124/213 (58%) |
| 0.585 | 89.1% | 97.12% | 170 | 140/213 (66%) |
| 0.600 | 88.4% | 97.25% | 186 | 144/213 (68%) |
| 0.650 | 85.9% | 97.79% | 241 | 159/213 (75%) |
| 0.700 | 83.2% | 98.35% | 302 | 174/213 (82%) |

Median confidence of wrong predictions: 0.505; median of correct: 0.925.

**Decision:** UI threshold 0.585 (97% rule). Chosen AFTER test evaluation, on VALIDATION data only, prompted by a real-world out-of-distribution example (laptop case on wooden bench -> cardboard @ 49%). Test-set metrics in metrics.json are unchanged.
