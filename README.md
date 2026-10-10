# Zurich Safe Cycling Routing

A reproducible cycling-route comparison for the Zurich model network and ETH Zentrum / ETH Hoenggerberg. Historical bicycle accidents inform a hierarchical Bayesian accident-intensity model. Four routing strategies compare distance, estimated time, and modeled risk exposure.

**Final balanced weights: time 0.8, risk 0.2.** All published benchmark results use the Bayesian scores at 08:00. Risks are relative model scores, not individual crash probabilities.

## Setup and run

Use Python 3.10+ and install Git LFS before cloning or fetching the processed risk table.

```bash
git lfs install
git lfs pull
python -m venv .venv
# Activate .venv using your shell, then:
python -m pip install -r requirements.txt
streamlit run frontend.py
```

## Reproduce the final analysis

From the repository root:

```bash
# Optional: rebuild risk scores from supplied raw accidents and cached OSM graph.
python scripts/update_bayesian_risk.py
# Evaluate all covered intersection origins to both ETH campuses.
python scripts/benchmark_all_campus_od.py
# Evaluate 11 time-risk weights on the same OD population.
python scripts/weight_sensitivity.py
# Generate a representative current-query route comparison.
python scripts/run_step2_pipeline.py --origin wiedikon --destination both_campuses --time-period 8
```

Bayesian fitting requires four chains per hour and is slower than routing. The benchmark must run before sensitivity analysis. The sensitivity script verifies the risk-table hash to prevent mixing models. Raw files are supplied in data/raw; the fitting script does not download accident data.

## Final results

08:00, 27,598 directed OD pairs, 110,392 routes; each OD has equal weight. Origins are covered OSM nodes with street_count >=3 and a directed path to the campus, not demand-weighted observed trips. The cached network has not been additionally clipped to the municipal boundary or consolidated into real-world intersections.

| Strategy | Mean risk exposure reduction | Mean time increase | Mean distance change | Mean extra time |
|---|---:|---:|---:|---:|
| Shortest | 19.66% | 7.34% | -3.54% | 1.42 min |
| Balanced (0.8 / 0.2) | 41.71% | 18.24% | +2.47% | 3.50 min |
| Safest | 52.67% | 94.85% | +52.72% | 19.01 min |

Percentages use the raw fastest route as the baseline separately for each OD, then average across OD pairs. The selected 0.8/0.2 weighting follows the full 11-weight sensitivity analysis; it is a chosen operating point, not a universal optimum.

- [Bayesian model](docs/hierarchical_bayesian_risk.md)
- [Benchmark and sensitivity methods](docs/benchmark_and_sensitivity.md)
- [Final benchmark](results/benchmark_all_campus_od/report.md)
- [Full sensitivity report](results/weight_sensitivity/report.md)
- [File guide](docs/file_explanation.md)
- [GitHub packaging](docs/github_upload.md)

![Time-risk trade-off](results/weight_sensitivity/tradeoff_curve.png)

## Data sources and interpretation

- [Stadt Zurich accident data](https://data.stadt-zuerich.ch/dataset/sid_dav_strassenverkehrsunfallorte): provider Bundesamt fuer Strassen ASTRA, 2011-2025; source portal specifies Creative Commons Attribution. Preserve attribution.
- [OpenStreetMap](https://www.openstreetmap.org/copyright): cycling network, ODbL; cached graph produced with OSMnx.

The Bayesian model uses length-years, not cyclist traffic volume, as its exposure proxy. Buffered accidents can contribute to multiple neighboring segments. The final score includes a heuristic road-class penalty and hourly percentile ranking. No held-out predictive validation has been performed; no real-world crash reduction is established. Current reports describe one hour; travel time is estimated using road-class speeds, without elevation or live traffic.
