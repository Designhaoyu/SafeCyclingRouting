# Step 3 interface contract

## Call

`backend.run_routing_pipeline_from_ui(origin_lat, origin_lon, time_period, destination_key)` returns the route GeoJSON path and summary CSV path. Coordinates use WGS84 latitude/longitude. destination_key is eth_zentrum, eth_hoenggerberg, or both_campuses. Hour labels such as 8, h08 and 08:00 are accepted.

## Inputs

- data/raw/zurich_bike_graph.graphml: cached directed OSM graph.
- data/processed/zurich_hourly_edge_safety_score.csv: active Bayesian table, fetched using Git LFS.
- Score identity: u, v, key, edge_id; period: time_period; risk_score in [0,1], safety_score=1-risk_score.

## Outputs

- results/step2_current_routes.geojson: one feature per route edge; route_type, risk_score, length_m and travel_time_s for rendering.
- results/step2_route_summary.csv: per-route distance, estimated minutes, model exposure, mean risk and weights.
- results/step2_route_summary.md: current-query explanation.
- results/recommended_route_map.html: Folium map produced by render_final_map.

Current-query exports represent one chosen origin and selected destinations. The exhaustive benchmark is stored separately. All four strategies are retained; the final balanced route uses time=0.8 and risk=0.2.
