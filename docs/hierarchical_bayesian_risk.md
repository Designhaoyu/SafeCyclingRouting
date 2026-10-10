# Hierarchical Bayesian accident risk update

Run `python scripts/update_bayesian_risk.py` from the repository root. This is the canonical Step 1 pipeline. The obsolete fixed-smoothing notebook has been removed.

For each clock hour, let y_i be buffered bicycle-accident counts over the available years and E_i be segment length (km, floored at 0.01 km) times observed calendar-year coverage. The model is:

- y_i | lambda_i ~ Poisson(E_i * lambda_i)
- lambda_i | mu_g ~ Gamma(shape=2, rate=2/mu_g), g = OSM road class
- log(mu_g) | log(mu_city) ~ Normal(log(mu_city), 1)
- log(mu_city) ~ Normal(0, 5)

Road-class and city means are jointly inferred, rather than fitted and plugged in. Edge rates are integrated out for hyperparameter sampling; their conditional Gamma posteriors are then integrated over sampled hyperparameters. Four chains use 1,200 warmup and 1,200 retained iterations each. Warmup adapts proposal scales; retained draws do not adapt. Classical R-hat and autocorrelation ESS are checked for all sampled hyperparameters. Activation requires max R-hat <1.05 and minimum ESS >=100 for every hour. These diagnostics are less robust than rank-normalized split R-hat and do not establish predictive validity.

The conditional posterior mean is (y_i+2)/(E_i+2/mu_g), a weighted blend of the raw rate y_i/E_i and mu_g. Sparse counts are regularized and zero counts do not imply zero latent risk. The prior precision (shape=2) and road-class log standard deviation (1) are fixed, explicit modeling choices; they are not estimated and require subsequent sensitivity analysis.

The 50m spatial assignment matches the legacy method. Exact reverse-direction physical geometries are consolidated before fitting. One accident can still be counted near several different segments; the resulting Poisson likelihood is a working model with dependent spatial observations, so uncertainty can be optimistic. Segment length-years are a spatial opportunity proxy, not cyclist volume or person-distance exposure. The rates are neighborhood accident-intensity estimates, not individual crash probabilities. Year-to-year network/traffic changes and severity are not modeled. Hours are fitted separately and do not borrow strength across neighboring hours.

For routing compatibility, posterior means are min-max normalized per hour, combined with the existing road-class penalty (3 * normalized intensity + penalty), and percentile ranked to risk_score. safety_score = 1-risk_score. Conditional posterior intervals refer to latent accident intensity, not the final percentile risk score. Existing routing objectives are unchanged.

Outputs under results/bayesian_risk include the immutable first pre-update backup, candidate scores, physical-segment/hour posterior means and uncertainty, sampling diagnostics, and score changes on matched legacy edges. Default scores are replaced only after diagnostics pass. Final benchmark and example routes use this model and balanced time/risk weights of 0.8/0.2. Rebuilding scores requires rerunning downstream analyses.

No held-out temporal predictive validation has yet been performed. Partial pooling and final trade-off evaluation are implemented; improved out-of-sample predictive accuracy is not established. See benchmark_and_sensitivity.md for final evaluation methods.

## Final inference diagnostics

8,753 bicycle accidents; 25,481 consolidated physical segments; 45,254 directed edges; 24 hours. Maximum classical R-hat across all hours: 1.01012; minimum autocorrelation ESS: 598.98. These checks establish acceptable mixing under the stated diagnostics, not model validity. The 95% latent-rate intervals use 240 conditional posterior mixture samples and have Monte Carlo error. Posterior means and standard deviations integrate all 4,800 retained hyperparameter draws per hour.

The active score CSV is Git LFS tracked. Full posterior and backup CSVs are local ignored outputs; compact posterior_summary.csv and posterior_sample_h08.csv are retained for review.
