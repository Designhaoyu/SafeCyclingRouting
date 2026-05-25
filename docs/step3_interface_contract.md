# Step 3 Interface Contract

This document explains how Step 3 should call Step 2 after the GUI user chooses a starting point.

## Concept

Step 2 does not precompute routes from every Zurich point to the two ETH campuses. Instead:

1. Step 3 lets the user choose a starting point on the map.
2. Step 3 passes that coordinate to Step 2.
3. Step 2 snaps the coordinate to the nearest node in the Zurich cycling graph.
4. Step 2 computes routes to the fixed campus destinations.
5. Step 3 reads the generated GeoJSON and CSV outputs.

The full Zurich cycling graph is stored in:

```text
data/raw/zurich_bike_graph.graphml
```

The current user-query routes are stored in:

```text
results/step2_current_routes.geojson
```

## Step 3 Input to Step 2

Step 3 should provide:

- `origin_lat`: user-selected latitude.
- `origin_lon`: user-selected longitude.
- `origin_name`: optional readable label.
- `destination`: usually `both_campuses`.
- `time_period`: optional, for example `8` if Step 1 provides hourly risk scores.
- `safety_file`: optional real Step 1 CSV.

The default `time_period` is `8`. Step 3 should pass a different `time_period` value when the GUI user selects another hour.

Example command with the default real hourly safety file:

```bash
python scripts/run_step2_pipeline.py --origin-lat 47.37139 --origin-lon 8.51680 --origin-name "User selected start" --destination both_campuses
```

Example command with real hourly Step 1 safety scores:

```bash
python scripts/run_step2_pipeline.py --safety-file data/processed/zurich_hourly_edge_safety_score.csv --time-period 8 --origin-lat 47.37139 --origin-lon 8.51680 --origin-name "User selected start" --destination both_campuses
```

The hourly label in the CSV may be written as `8`, `08`, `h08`, `hour_08`, or `08:00`; Step 2 treats these as the same hour.

## Step 2 Output for Step 3

Step 3 should read:

```text
results/step2_current_routes.geojson
results/step2_route_summary.csv
```

Optional human-readable output:

```text
results/step2_route_summary.md
```

Optional verification image:

```text
results/step2_current_route_plot.png
```

## GeoJSON Structure

`results/step2_current_routes.geojson` is a GeoJSON `FeatureCollection`.

Each feature is one route link/edge, not one complete route. A complete route is split into many `LineString` features so Step 3 can color each road segment by its own risk value.

With `--destination both_campuses`, Step 2 computes:

```text
4 route strategies * 2 campus destinations = 8 complete routes
```

Those complete routes are exported as many link features. Each link feature has:

- `geometry`: one link `LineString` in longitude/latitude order.
- `properties.route_id`: group id for rebuilding a complete route from links.
- `properties.route_type`: route strategy name.
- `properties.origin_name`: user-selected origin label.
- `properties.destination_name`: campus destination.
- `properties.segment_index`: order of this link within its route.
- `properties.u`, `properties.v`, `properties.key`, `properties.edge_id`: graph edge identifiers.
- `properties.risk_score`: risk value for this exact link.
- `properties.safety_score`: safety value for this exact link.
- `properties.length_m`: link length.
- `properties.travel_time_s`: link travel time.
- `properties.highway`: OSM road type.
- `properties.route_total_distance_km`: full route distance.
- `properties.route_estimated_travel_time_min`: full route estimated travel time.
- `properties.route_mean_risk_score`: full route mean risk.

## Important Clarification

The GeoJSON output is not the whole Zurich map. It contains only the routes for the current user query.

The whole Zurich network is used internally by Step 2 through the OSMnx graph cache. Step 3 usually does not need to render that full graph unless the visualization team specifically wants a background network layer.
