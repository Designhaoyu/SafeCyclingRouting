# Step 2 Algorithm Explanation

## Graph Representation

The Zurich cycling network is represented as a `networkx.MultiDiGraph`.

- A node is a street-network point, usually an intersection or path connection.
- An edge is a road or cycling segment between two nodes.
- A multigraph is used because OpenStreetMap can contain multiple edges between the same two nodes.
- A directed graph is used because some streets or paths can be direction-specific.

For each edge, Step 2 stores:

- `length`: distance in meters.
- `highway`: OSM road/path category.
- `speed_kph`: estimated cycling speed.
- `travel_time_s`: estimated cycling time.
- `safety_score`: safety score from the real Step 1 hourly file.
- `risk_score`: derived as `1 - safety_score` when Step 1 provides only safety.
- `risk_cost`: `risk_score * length`, representing distance-weighted risk exposure.

## Step 1 Safety Input

The routing algorithm now uses the real hourly Step 1 file:

```text
data/processed/zurich_hourly_edge_safety_score.csv
```

The file contains hourly safety scores with `time_period` values such as:

```text
h00, h01, ..., h23
```

When running Step 2, `--time-period 8` is treated as `h08`. Equivalent labels such as `08`, `h08`, `hour_08`, and `08:00` are also accepted.

## Why Edge Weights Matter

Shortest path algorithms find the path with the smallest total edge weight. By changing the edge weight, the definition of "best route" changes.

- `length` produces the shortest-distance route.
- `travel_time_s` produces the fastest estimated route.
- `risk_cost` produces the lowest-risk-exposure route.
- a combined cost produces a balanced route.

## Route Strategies

### `shortest_distance`

Minimizes:

```text
length
```

### `fastest_time`

Minimizes:

```text
travel_time_s
```

### `safest_route`

Minimizes:

```text
risk_cost = risk_score * length
```

### Balanced Routes

Balanced routes combine efficiency and safety:

```text
combined_cost = alpha * normalized_time
              + beta * normalized_risk_cost
```

`alpha` controls the importance of efficiency. `beta` controls the importance of safety.

The exported default balanced route uses:

- `alpha = 0.5`
- `beta = 0.5`

This gives equal emphasis to time and safety exposure.

Here `risk_cost = risk_score * length`, so the balanced route considers distance-weighted risk exposure rather than only the edge's raw risk probability. The values are normalized before being combined because seconds and risk costs are measured on different scales.

## Step 3 Use Case

For Step 3, the full Zurich graph is loaded internally. The GUI should pass a user-selected origin coordinate to Step 2. Step 2 snaps that coordinate to the nearest graph node and computes routes to the fixed campus destinations:

- ETH Zentrum
- ETH Hoenggerberg

The generated GeoJSON contains only the current query routes, not the whole Zurich map. Each complete route is split into individual link features so Step 3 can color every road segment by its own `risk_score`.
