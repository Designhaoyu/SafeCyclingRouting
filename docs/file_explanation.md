# Repository file guide

| Path | Purpose |
|---|---|
| frontend.py | Streamlit interface and route dashboard |
| backend.py | GUI-to-routing wrapper and Folium map renderer |
| src/zurich_safe_routing/config.py | Paths, campuses, road-class speeds |
| src/zurich_safe_routing/bayesian_risk.py | Hierarchical Gamma-Poisson posterior inference |
| src/zurich_safe_routing/safety_data.py | Hour filtering and edge score attachment |
| src/zurich_safe_routing/graph_builder.py | Cached OSM graph loading and travel times |
| src/zurich_safe_routing/routing.py | Four routing objectives; default balanced 0.8/0.2 |
| src/zurich_safe_routing/exports.py | Current-query CSV, GeoJSON, Markdown, plot |
| scripts/update_bayesian_risk.py | Canonical Step 1; fits all 24 hours and activates scores after diagnostics |
| scripts/run_step2_pipeline.py | Canonical route-comparison CLI |
| scripts/benchmark_all_campus_od.py | Final all-intersection-to-campus evaluation |
| scripts/weight_sensitivity.py | Full 11-weight sensitivity sweep |
| data/raw/ | Government accident CSV and cached OSM graph |
| data/processed/zurich_hourly_edge_safety_score.csv | Active Bayesian score table; Git LFS |
| results/bayesian_risk/ | Sampling diagnostics and compact posterior summary/sample |
| results/benchmark_all_campus_od/ | Final 0.8/0.2 benchmark, OD population, validation, plots |
| results/weight_sensitivity/ | All weights and final selected operating point |
| results/step2_* | Representative Wiedikon-to-campus query at 08:00 |
| results/recommended_route_map.html | Generated interactive map for the current example |
| docs/ | Model, evaluation, algorithm, GUI contract and upload documentation |

Raw posterior rates and per-OD detailed comparisons remain local, reproducible artifacts excluded by .gitignore. There is one canonical script per stage; old notebooks, duplicate root exports and preliminary benchmarks have been removed.
