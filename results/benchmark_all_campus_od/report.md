# All intersection-to-campus OD benchmark

08:00; 27,598 directed OD pairs; 110,392 routes. Four unchanged routing objectives; balanced alpha=0.8, beta=0.2.

| Scope | Strategy | Mean risk reduction | Mean time penalty | Mean distance penalty | Mean extra minutes | Risk improved |
|---|---|---:|---:|---:|---:|---:|
| all_campuses | balanced_route | 41.71% | 18.24% | 2.47% | 3.50 | 97.30% |
| all_campuses | fastest_time | 0.00% | 0.00% | 0.00% | 0.00 | 0.00% |
| all_campuses | safest_route | 52.67% | 94.85% | 52.72% | 19.01 | 99.48% |
| all_campuses | shortest_distance | 19.66% | 7.34% | -3.54% | 1.42 | 88.29% |
| eth_zentrum | balanced_route | 40.62% | 21.21% | 3.53% | 3.39 | 98.87% |
| eth_zentrum | fastest_time | 0.00% | 0.00% | 0.00% | 0.00 | 0.00% |
| eth_zentrum | safest_route | 51.11% | 98.48% | 53.69% | 16.20 | 99.73% |
| eth_zentrum | shortest_distance | 18.73% | 7.92% | -3.64% | 1.24 | 94.09% |
| eth_hoenggerberg | balanced_route | 42.80% | 15.26% | 1.41% | 3.60 | 95.74% |
| eth_hoenggerberg | fastest_time | 0.00% | 0.00% | 0.00% | 0.00 | 0.00% |
| eth_hoenggerberg | safest_route | 54.23% | 91.21% | 51.75% | 21.82 | 99.22% |
| eth_hoenggerberg | shortest_distance | 20.59% | 6.76% | -3.43% | 1.60 | 82.48% |

## Method and limitations

- Origins are all current cached OSM nodes with street_count >= 3 and at least one incident edge present in the hourly safety table. Each campus destination is snapped to the existing graph. No additional municipal boundary clipping or physical-junction consolidation was performed.
- Reachable OD counts: {'eth_zentrum': 13799, 'eth_hoenggerberg': 13799}. The destination itself is excluded; unreachable origins are listed in excluded_origins.csv.
- This is an exhaustive enumeration of the defined model population at 08:00, not observed OD flows. Every OD receives equal weight; no traffic demand data are used. Shared origins and overlapping routes mean OD results are correlated.
- Risk exposure = sum(edge risk score * length in metres). Travel time follows existing road-class speeds. Results are model-based, not observed crash-probability reductions.
- Paired percentages use each OD baseline denominator, then arithmetic means across OD pairs. Medians and 10th/90th percentiles are included. Zero baseline risk, if any, yields undefined percentage reduction and is counted separately.
- No sample bootstrap confidence intervals are reported for this complete finite OD population. Risk-model uncertainty and effects of time of day remain outside this evaluation.
- 0 graph edges without matched scores use the existing default risk score of 0.5; paths can traverse these edges.
- Reverse routing was checked against 80 original forward searches: objective costs agree. All 110,392 route results were checked for the respective shortest/fastest/safest metric ordering. Equal-cost ties may produce alternate equally optimal paths.

Run: `D:/software/Anaconda/python.exe scripts/benchmark_all_campus_od.py`
