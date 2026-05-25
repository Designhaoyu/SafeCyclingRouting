# Step 2 Code Walkthrough

This walkthrough explains the Step 2 code files after integration with the real hourly Step 1 safety data.

The main entry point is:

```text
scripts/run_step2_pipeline.py
```

## Overall Pipeline

1. Load configuration and create project folders.
2. Load the Zurich cycling graph from `data/raw/zurich_bike_graph.graphml`, or download it with OSMnx if needed.
3. Load real hourly edge safety scores from `data/processed/zurich_hourly_edge_safety_score.csv`.
4. Filter safety scores by `time_period`, for example hour `8`.
5. Attach safety/risk values to graph edges.
6. Prepare routing weights.
7. Compute route strategies to one or both fixed campus destinations.
8. Export GeoJSON, CSV, Markdown, and a verification plot.

## `config.py`

`Location` stores a readable name plus latitude and longitude.

`RoutingConfig` stores:

- project paths.
- OSM place name and network type.
- graph cache path.
- real Step 1 safety path: `data/processed/zurich_hourly_edge_safety_score.csv`.
- output paths.
- named locations such as ETH Zentrum, ETH Hoenggerberg, Zurich HB, and Wiedikon.
- fixed campus destination keys.
- estimated cycling speeds by OSM road type.

## `graph_builder.py`

`build_or_load_graph()` returns the Zurich cycling graph.

It prefers the cached graph:

```text
data/raw/zurich_bike_graph.graphml
```

If the cache is missing, it can download the graph with OSMnx.

`ensure_edge_lengths_and_times()` ensures each edge has:

- `length`
- `highway`
- `speed_kph`
- `travel_time_s`
- `edge_id`

`nearest_node()` snaps a latitude/longitude origin from Step 3 to the nearest graph node.

## `safety_data.py`

`load_safety_scores(path, time_period)` loads the real Step 1 edge safety file.

Required identifier columns:

- `u`
- `v`
- `key`
- `edge_id`

Score columns:

- `safety_score` or `risk_score`

If only `safety_score` is present, Step 2 derives:

```text
risk_score = 1 - safety_score
```

The hourly labels are matched flexibly. These all refer to hour 8:

```text
8
08
h08
hour_08
08:00
```

`attach_safety_scores_to_graph()` attaches:

- `risk_score`
- `safety_score`
- `risk_cost`

to each graph edge.

## `routing.py`

`RouteStrategy` defines one objective, such as shortest distance or safest route.

`RouteResult` stores one computed route and metrics:

- route type.
- origin and destination.
- path nodes.
- exact edge triplets.
- total distance.
- estimated travel time.
- total risk exposure.
- mean risk score.
- combined cost.

`prepare_edge_weights()` creates:

- `weight_distance`
- `weight_time`
- `weight_safety`
- normalized time and risk-exposure attributes for balanced routing.

`compare_route_strategies()` computes all default route strategies between one origin and one destination.

## `exports.py`

`export_route_outputs()` writes:

```text
results/step2_current_routes.geojson
results/step2_route_summary.csv
results/step2_route_summary.md
results/step2_current_route_plot.png
```

Step 3 should mainly read:

```text
results/step2_current_routes.geojson
results/step2_route_summary.csv
```

The GeoJSON file is exported at link level: every Feature is one graph edge segment from one computed route. Important per-link properties include `route_type`, `risk_score`, `length_m`, `travel_time_s`, `u`, `v`, `key`, and `edge_id`.

## `scripts/run_step2_pipeline.py`

Default command:

```bash
python scripts/run_step2_pipeline.py
```

Default behavior:

- safety file: `data/processed/zurich_hourly_edge_safety_score.csv`
- time period: `8`
- origin: `wiedikon`
- destination: `both_campuses`

Step 3-style command:

```bash
python scripts/run_step2_pipeline.py --time-period 8 --origin-lat 47.37139 --origin-lon 8.51680 --origin-name "User selected start" --destination both_campuses
```

The script then regenerates the current route outputs for Step 3.
