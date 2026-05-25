# Step 2 Route Summary

This file compares route strategies produced by the Step 2 routing algorithm.
Risk values come from the selected Step 1 edge safety file.

| route_type | origin_name | destination_name | origin_node | destination_node | weight_attribute | number_of_edges | estimated_travel_time_min | total_risk_exposure | mean_risk_score | combined_cost | alpha | beta | base_weight | total_distance_km |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| shortest_distance | Wiedikon | ETH Zentrum | 3906839266 | 4324863889 | weight_distance | 76 | 13.84 | 2996.82 | 0.8598 | 3485.638 |  |  |  | 3.486 |
| fastest_time | Wiedikon | ETH Zentrum | 3906839266 | 4324863889 | weight_time | 94 | 12.98 | 3149.89 | 0.8669 | 778.6372 |  |  |  | 3.634 |
| safest_route | Wiedikon | ETH Zentrum | 3906839266 | 4324863889 | weight_safety | 102 | 17.52 | 1851.97 | 0.4246 | 1851.9697 |  |  |  | 4.362 |
| balanced_route | Wiedikon | ETH Zentrum | 3906839266 | 4324863889 | weight_balanced_time_alpha_0_5_beta_0_5 | 98 | 15.97 | 1900.2 | 0.4596 | 0.6137 | 0.5 | 0.5 | time | 4.134 |
| shortest_distance | Wiedikon | ETH Hoenggerberg | 3906839266 | 29353925 | weight_distance | 91 | 25.03 | 4328.12 | 0.7313 | 5918.0665 |  |  |  | 5.918 |
| fastest_time | Wiedikon | ETH Hoenggerberg | 3906839266 | 29353925 | weight_time | 110 | 22.69 | 4938.98 | 0.7869 | 1361.2625 |  |  |  | 6.276 |
| safest_route | Wiedikon | ETH Hoenggerberg | 3906839266 | 29353925 | weight_safety | 145 | 37.12 | 2992.02 | 0.3554 | 2992.0163 |  |  |  | 8.418 |
| balanced_route | Wiedikon | ETH Hoenggerberg | 3906839266 | 29353925 | weight_balanced_time_alpha_0_5_beta_0_5 | 95 | 24.26 | 3479.38 | 0.5773 | 1.0282 | 0.5 | 0.5 | time | 6.027 |

## Interpretation

From Wiedikon to ETH Zentrum, the shortest route is `shortest_distance` at 3.49 km, the fastest route is `fastest_time` at 13.0 minutes, and the lowest mean-risk route is `safest_route` with mean risk 0.425. From Wiedikon to ETH Hoenggerberg, the shortest route is `shortest_distance` at 5.92 km, the fastest route is `fastest_time` at 22.7 minutes, and the lowest mean-risk route is `safest_route` with mean risk 0.355. The balanced route trades some efficiency for lower risk by adding normalized risk exposure to the routing cost.
