# Routing algorithm

Load the cached directed OSM bicycle graph, attach the requested hourly Bayesian risk_score by u/v/key, and estimate edge travel time from road-class speeds. Missing scores use 0.5; the final Bayesian table currently covers every graph edge.

| Strategy | Edge objective |
|---|---|
| shortest_distance | length_m |
| fastest_time | travel_time_s |
| safest_route | risk_score * length_m |
| balanced_route | 0.8 * time_norm + 0.2 * risk_cost_norm |

Normalization is min-max across graph edges for the requested hour. The coefficients are weights on normalized edge costs, not percentages of trip time or safety gains. Risk scores are relative ranks, not crash probabilities. Min-max subtraction can change the effect of path edge counts; pure normalized endpoint objectives need not reproduce raw objectives.

NetworkX weighted shortest paths choose node sequences. Between parallel edges the edge with the lowest selected objective is chosen. Route exposure sums risk_score * length_m; route mean risk is exposure / distance. Balanced routing includes time and exposure; distance is reported but not directly weighted.

The GUI computes only the requested origin-to-campus routes. The offline benchmark computes all covered intersection-to-campus ODs using reverse Dijkstra. Both use the same weights. See [benchmark methods](benchmark_and_sensitivity.md).

## Implementation flow

`config.py` defines paths, campuses and speeds; `graph_builder.py` loads the graph and travel times; `safety_data.py` attaches hourly scores; `routing.py` computes paths; `exports.py` writes summaries and geometry. `backend.py` connects this pipeline to `frontend.py`.

### Edge-count effect of normalization

For edge cost x, summing min-max costs along n edges gives `(sum(x) - n * min(x)) / (max(x) - min(x))`. A positive minimum creates an edge-count-dependent discount, so paths with more edges can be favored relative to scaling the total cost. The time and exposure components both have this effect. Reported evaluations retain this implementation; changing it requires recomputing the benchmark and weight selection.
