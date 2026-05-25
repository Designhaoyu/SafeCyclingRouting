# Zurich Safe Cycling Route Recommender

This repository contains the Step 2 routing algorithm for the Zurich Safe Cycling Route Recommender. It is now configured to use the real Step 1 hourly edge safety file:

```text
data/processed/zurich_hourly_edge_safety_score.csv
```

Step 2 does not build the Step 3 GUI. Instead, it provides the routing backend that Step 3 can call after a user selects a starting point.

## Current Scope

Step 2 models Zurich's cycling network as a weighted graph. Each edge stores distance, estimated cycling time, road type, safety/risk score, and route-specific cost values.

The algorithm compares:

- `shortest_distance`
- `fastest_time`
- `safest_route`
- `balanced_route`

The destination can be fixed to both ETH campuses:

- ETH Zentrum
- ETH Hoenggerberg

The origin can be a named test point or a user-selected latitude/longitude from the Step 3 GUI.

## Installation

From the project root:

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

On macOS or Linux:

```bash
source .venv/bin/activate
```

## Run Step 2

Default run:

```bash
python scripts/run_step2_pipeline.py
```

By default, this uses:

```text
safety file: data/processed/zurich_hourly_edge_safety_score.csv
time period: 8
origin: wiedikon
destination: both_campuses
```

Step 3-style run with a user-selected origin:

```bash
python scripts/run_step2_pipeline.py --origin-lat 47.37139 --origin-lon 8.51680 --origin-name "User selected start" --destination both_campuses
```

Use a different hour:

```bash
python scripts/run_step2_pipeline.py --time-period 17 --origin-lat 47.37139 --origin-lon 8.51680 --origin-name "User selected start" --destination both_campuses
```

The real hourly safety file uses labels like `h00`, `h01`, ..., `h23`. The command accepts equivalent labels such as `8`, `08`, `h08`, `hour_08`, and `08:00`.

## Expected Outputs

The pipeline writes:

- `results/step2_current_routes.geojson`
- `results/step2_route_summary.csv`
- `results/step2_route_summary.md`
- `results/step2_current_route_plot.png`

For Step 3, the most important files are:

```text
results/step2_current_routes.geojson
results/step2_route_summary.csv
```

The GeoJSON is regenerated for the current user-selected origin. It is not the whole Zurich map and not a database of all possible routes. Each GeoJSON feature is one route link/edge, not one complete route, so Step 3 can color each road segment by its own `risk_score`.

## Step 1 Safety File Schema

The current real Step 1 file is:

```text
data/processed/zurich_hourly_edge_safety_score.csv
```

Expected columns:

- `u`
- `v`
- `key`
- `edge_id`
- `safety_score` or `risk_score`
- `time_period`

If only `safety_score` is present, Step 2 derives:

```text
risk_score = 1 - safety_score
```

If only `risk_score` is present, Step 2 derives:

```text
safety_score = 1 - risk_score
```

## Project Structure

```text
data/
  processed/
    zurich_hourly_edge_safety_score.csv
  raw/
    zurich_bike_graph.graphml
docs/
  file_explanation.md
  step3_handoff_guide.md
  step3_interface_contract.md
  step2_algorithm_explanation.md
  step2_code_walkthrough.md
results/
  step2_route_summary.csv
  step2_route_summary.md
  step2_current_routes.geojson
  step2_current_route_plot.png
scripts/
  run_step2_pipeline.py
src/
  zurich_safe_routing/
    config.py
    graph_builder.py
    safety_data.py
    routing.py
    exports.py
requirements.txt
```

For Step 3 handoff instructions, read:

```text
docs/step3_handoff_guide.md
```
