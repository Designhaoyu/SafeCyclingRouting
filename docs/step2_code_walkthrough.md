# Code walkthrough

1. config.py defines project-relative paths, campus coordinates and cycling speed assumptions.
2. graph_builder.py loads the cached OSM graph and prepares edge lengths / travel times. Final evaluations disable synthetic fallback.
3. safety_data.py selects a clock hour and joins risk_score to directed edge identities. safety_score is 1-risk_score.
4. routing.py prepares raw and normalized objectives, computes four strategies and selects concrete parallel edges. Balanced weights are time=0.8 and risk=0.2.
5. exports.py writes current-query results under results/.
6. backend.py provides the GUI wrapper and writes results/recommended_route_map.html; frontend.py displays the routes and dashboard.

Before routing, scripts/update_bayesian_risk.py rebuilds the active score table using bayesian_risk.py. Sampling diagnostics and posterior summaries document inference. Offline evaluation is in scripts/benchmark_all_campus_od.py and scripts/weight_sensitivity.py. See the model and benchmark documents for equations, denominators, and limitations.
