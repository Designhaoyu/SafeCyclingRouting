# Weight sensitivity with Bayesian risk

08:00, 27,598 equal-weight campus OD pairs, 11 weights, 303,578 routes. Existing balanced objective: alpha * time_norm + (1-alpha) * risk_cost_norm. Distance is an evaluation metric, not an optimization objective. Baseline is the raw fastest-time route.

| Time alpha | Risk beta | Mean risk reduction | Mean time increase | Mean distance increase | Mean extra min |
|---:|---:|---:|---:|---:|---:|
| 0.0 | 1.0 | 52.67% | 94.95% | 52.79% | 19.03 |
| 0.1 | 0.9 | 52.52% | 73.49% | 37.63% | 14.70 |
| 0.2 | 0.8 | 52.14% | 61.44% | 29.15% | 12.38 |
| 0.3 | 0.7 | 51.69% | 53.96% | 24.13% | 10.79 |
| 0.4 | 0.6 | 50.96% | 46.47% | 19.25% | 9.03 |
| 0.5 | 0.5 | 50.01% | 40.11% | 15.20% | 7.70 |
| 0.6 | 0.4 | 48.24% | 32.52% | 10.48% | 5.98 |
| 0.7 | 0.3 | 45.31% | 24.36% | 5.87% | 4.52 |
| 0.8 | 0.2 | 41.71% | 18.24% | 2.47% | 3.50 |
| 0.9 | 0.1 | 30.54% | 8.10% | -1.70% | 1.61 |
| 1.0 | 0.0 | -0.26% | 0.00% | -0.01% | 0.00 |

Example constraint-based selection: among tested weights with mean time increase <=15% and mean distance increase <=10%, alpha=0.9, beta=0.1 yields the greatest mean risk reduction (30.54%). These thresholds are illustrative, not approved requirements; mean limits do not guarantee limits for every OD.

The user-selected default weight is time=0.8, risk=0.2; the full sweep is retained for comparison. No unique overall optimum is claimed. Values are model exposure reductions, not measured accident reductions. This is a discrete 0.1 grid at one hour; finer weights and other hours can change the preferred setting.

Endpoint caution: min-max normalization subtracts a constant per traversed edge. Therefore alpha=0 and alpha=1 do not necessarily reproduce raw safest and raw fastest routes; endpoint checks are in metadata.json. This analysis preserves the existing implementation.
