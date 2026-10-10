# GUI handoff

Run `streamlit run frontend.py` from the repository root after installing requirements and fetching the Git LFS risk table.

The user chooses origin, ETH campus destination and clock hour. frontend.py calls backend.run_routing_pipeline_from_ui, which loads the graph, filters hourly scores, computes routes and exports CSV/GeoJSON. backend.render_final_map renders the selected outputs and saves results/recommended_route_map.html.

The active risk model is hierarchical Bayesian; the final balanced objective is 0.8 normalized time + 0.2 normalized exposure. Lower risk_score means lower relative model risk; safety_score=1-risk_score. Report modeled risk exposure, not accident probability. Summary cards use estimated road-class travel times.

Canonical file paths and interface fields are in [interface contract](step3_interface_contract.md). Full offline benchmark and sensitivity outputs are independent of the current GUI query. A new query replaces current-query files; it does not overwrite the evaluation population.
