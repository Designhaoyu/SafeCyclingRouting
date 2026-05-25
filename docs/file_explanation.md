# File-by-File Explanation

This document explains the current Step 2 project structure. The routing pipeline now uses the real hourly Step 1 safety file:

```text
data/processed/zurich_hourly_edge_safety_score.csv
```

## `README.md`

- Type: documentation
- Purpose: project overview, installation, run commands, and expected outputs.
- Step: general setup and Step 2 usage.

## `requirements.txt`

- Type: dependency specification
- Purpose: lists required Python packages such as `osmnx`, `networkx`, `pandas`, `geopandas`, `shapely`, and `matplotlib`.
- Step: general setup.

## `scripts/run_step2_pipeline.py`

- Type: executable Python script
- Purpose: main Step 2 entry point for Step 3.
- Default safety input: `data/processed/zurich_hourly_edge_safety_score.csv`.
- Default time period: `8`, matching `h08` in the real hourly file.
- Main Step 3 options:
  - `--origin-lat`
  - `--origin-lon`
  - `--origin-name`
  - `--destination both_campuses`
  - `--time-period`
  - `--safety-file`
- Generates:
  - `results/step2_current_routes.geojson`
  - `results/step2_route_summary.csv`
  - `results/step2_route_summary.md`
  - `results/step2_current_route_plot.png`

## `src/zurich_safe_routing/config.py`

- Type: configuration code
- Purpose: stores project paths, graph cache path, real safety file path, named locations, fixed campus destinations, and cycling speed assumptions.
- Important path:
  - `real_safety_path = data/processed/zurich_hourly_edge_safety_score.csv`

## `src/zurich_safe_routing/graph_builder.py`

- Type: routing graph code
- Purpose: loads or downloads the Zurich cycling graph, ensures edge lengths and travel times, and maps user coordinates to nearest graph nodes.
- Uses:
  - `data/raw/zurich_bike_graph.graphml`
- Step: Step 2 graph preparation.

## `src/zurich_safe_routing/safety_data.py`

- Type: safety data loading code
- Purpose: loads the real Step 1 hourly edge safety file and attaches safety/risk values to graph edges.
- Accepts:
  - `safety_score`
  - `risk_score`
  - or one of the two, deriving the other as `1 - score`.
- Supports hourly labels such as `8`, `08`, `h08`, `hour_08`, and `08:00`.

## `src/zurich_safe_routing/routing.py`

- Type: routing algorithm code
- Purpose: creates route strategies, computes shortest paths with NetworkX, and summarizes route metrics.
- Strategies:
  - `shortest_distance`
  - `fastest_time`
  - `safest_route`
  - `balanced_route`

## `src/zurich_safe_routing/exports.py`

- Type: output code
- Purpose: exports route results for Step 3.
- Generates:
  - GeoJSON route file.
  - CSV route summary.
  - Markdown summary.
  - PNG verification plot.

## `data/processed/zurich_hourly_edge_safety_score.csv`

- Type: real Step 1 processed data
- Purpose: hourly edge-level safety scores.
- Important columns:
  - `u`
  - `v`
  - `key`
  - `edge_id`
  - `time_period`
  - `safety_score`
  - `highway`
  - `risk_source`
- Step: Step 1 output, Step 2 input.

## `data/raw/zurich_bike_graph.graphml`

- Type: graph cache
- Purpose: stores the Zurich cycling network used by Step 2.
- Step: Step 2 input.

## `results/step2_current_routes.geojson`

- Type: generated Step 2 output
- Purpose: route-link geometries for the current user-selected origin and fixed campus destination query.
- Step 3 use: draw route links on the map and color each link by `properties.risk_score`.
- Important note: this is not the full Zurich map. It contains only the current query routes, split into individual route links.

## `results/step2_route_summary.csv`

- Type: generated Step 2 output
- Purpose: table of route metrics for Step 3 UI panels.
- Step 3 use: display route type, destination, distance, time, and risk.

## `results/step2_route_summary.md`

- Type: generated human-readable output
- Purpose: report-friendly route summary.

## `results/step2_current_route_plot.png`

- Type: generated verification image
- Purpose: simple static plot for checking route outputs.

## `docs/step3_handoff_guide.md`

- Type: handoff documentation
- Purpose: Chinese guide for Step 3 teammates.

## `docs/step3_interface_contract.md`

- Type: interface documentation
- Purpose: concise Step 2 to Step 3 contract.

## `docs/step2_code_walkthrough.md`

- Type: documentation
- Purpose: explains the current Step 2 code files.

## `docs/step2_algorithm_explanation.md`

- Type: documentation
- Purpose: explains the graph model, edge weights, route strategies, and alpha/beta trade-off.
