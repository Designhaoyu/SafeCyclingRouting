# Benchmark and weight sensitivity

## Evaluation population

The same Bayesian hourly risk table and cached directed cycling graph are used throughout. At 08:00 there are 13,823 intersection nodes (street_count >=3), all covered by the risk table. Excluding each destination itself and 23 unreachable origins gives 13,799 OD pairs per campus, 27,598 total. This is a finite network-node population with equal OD weights, not observed travel demand. Administrative boundary clipping and physical-junction consolidation are not performed.

## Metrics

- Distance: sum of edge lengths, reported in km.
- Estimated time: sum(length / road-class speed), reported in minutes.
- Model exposure R: sum(risk_score * length_m).
- Mean risk score: R / total_length_m.
- Risk reduction: 100 * (1 - R_strategy / R_fastest).
- Time or distance increase: 100 * (strategy / fastest - 1).

Compute percentages per OD, then average. Report medians and distribution measures as well. Reductions are not probabilities or observed accident effects. Shared routes and origins are correlated. No sampling confidence interval is needed for this exhaustive defined population; model uncertainty is not propagated into route comparisons.

## Benchmark

Run `python scripts/benchmark_all_campus_od.py`. Four objectives: raw length, raw time, raw exposure, and balanced normalized time/exposure with alpha=0.8, beta=0.2. Reverse single-source Dijkstra computes all origins efficiently while respecting original directed weights and concrete parallel-edge selection. Eighty forward searches check objective agreement; every route is checked for shortest/fastest/safest ordering. Equal-cost ties can choose different paths.

## Sensitivity

Run `python scripts/weight_sensitivity.py` after the benchmark. The score-file hash must match the benchmark metadata. Evaluate alpha=0,0.1,...,1 and beta=1-alpha: 303,578 routes. Distance is an evaluation metric, not a third objective. The 0.8/0.2 routes are checked against the final benchmark.

Selected operating point: alpha=0.8, beta=0.2. Mean modeled exposure reduction 41.71%, time increase 18.24%, distance increase 2.47%, extra time 3.50 minutes relative to fastest. The alternative alpha=0.9 yields 30.54%, 8.10%, -1.70%, and 1.61 minutes. Mean thresholds of 15% time and 10% distance in the report are an illustrative decision rule; they were not the user's final selection criteria and do not guarantee per-trip limits.

The full grid is retained to document the selection. Min-max normalization subtracts a constant per edge, so endpoint weights need not equal raw fastest/safest objectives. The endpoint checks are recorded rather than silently changing the algorithm. The analysis supports a chosen operating point, not a mathematically unique overall best route.

## Artifacts

Keep compact reports, summaries, OD coordinates, validation evidence, metadata, and figures in Git. Large route-level comparison CSVs are regenerated locally and ignored. Input SHA-256 hashes link results to specific graph and score files. Historical trials and old risk-model benchmarks are removed from final presentation.
