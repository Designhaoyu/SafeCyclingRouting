"""Run the Step 2 safe cycling route pipeline end to end."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from zurich_safe_routing.config import DEFAULT_CONFIG, ensure_project_directories
from zurich_safe_routing.exports import export_route_outputs
from zurich_safe_routing.graph_builder import build_or_load_graph, graph_source_label
from zurich_safe_routing.routing import compare_route_strategies, prepare_edge_weights
from zurich_safe_routing.safety_data import (
    attach_safety_scores_to_graph,
    load_safety_scores,
)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""

    parser = argparse.ArgumentParser(
        description="Compute Step 2 safe cycling routes for Zurich."
    )
    parser.add_argument(
        "--origin",
        default="wiedikon",
        help=(
            "Origin key from config.example_locations. Ignored if --origin-lat "
            "and --origin-lon are provided."
        ),
    )
    parser.add_argument(
        "--origin-lat",
        type=float,
        default=None,
        help="Custom origin latitude, for example from a GUI map click.",
    )
    parser.add_argument(
        "--origin-lon",
        type=float,
        default=None,
        help="Custom origin longitude, for example from a GUI map click.",
    )
    parser.add_argument(
        "--origin-name",
        default="Custom origin",
        help="Readable name used when --origin-lat and --origin-lon are provided.",
    )
    parser.add_argument(
        "--destination",
        default="both_campuses",
        help=(
            "Destination key from config.example_locations, or both_campuses "
            "to compute routes to ETH Zentrum and ETH Hoenggerberg."
        ),
    )
    parser.add_argument(
        "--time-period",
        default="8",
        help=(
            "Safety-score time period to use. The real Zurich hourly file uses "
            "h00-h23, so values like 8, 08, h08, or 08:00 are accepted. "
            "Default: 8."
        ),
    )
    parser.add_argument(
        "--safety-file",
        type=Path,
        default=None,
        help=(
            "Optional Step 1 safety CSV. If omitted, the real hourly file at "
            "data/processed/zurich_hourly_edge_safety_score.csv is used."
        ),
    )
    parser.add_argument(
        "--use-synthetic-graph",
        action="store_true",
        help="Use the small built-in graph instead of downloading OSM data.",
    )
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Ignore cached OSM graph and download a fresh one.",
    )
    parser.add_argument(
        "--skip-plot",
        action="store_true",
        help="Skip writing results/step2_current_route_plot.png.",
    )
    return parser.parse_args()


def main() -> int:
    """Run graph loading, safety attachment, routing, and exports."""

    args = parse_args()
    config = DEFAULT_CONFIG
    ensure_project_directories(config)

    origin = resolve_origin(args, config)
    destinations = resolve_destinations(args, config)

    graph = build_or_load_graph(
        config,
        force_download=args.force_download,
        use_synthetic_graph=args.use_synthetic_graph,
        allow_synthetic_fallback=True,
    )

    safety_path = args.safety_file or config.real_safety_path
    if not safety_path.exists():
        raise SystemExit(
            f"Safety file not found: {safety_path}. "
            "Provide the real Step 1 safety file with --safety-file."
        )

    safety_df = load_safety_scores(safety_path, time_period=args.time_period)
    graph = attach_safety_scores_to_graph(graph, safety_df)
    missing_safety = int(graph.graph.get("safety_scores_missing_edges", 0))
    if missing_safety:
        print(
            f"Warning: {missing_safety} graph edges did not match the safety file. "
            "They received the default risk score. Check that the safety file was "
            "generated for the same graph."
        )
    graph = prepare_edge_weights(graph)

    results = []
    for destination in destinations:
        try:
            results.extend(compare_route_strategies(graph, origin, destination, config=config))
        except ValueError as exc:
            if "same graph node" in str(exc):
                print(f"Skipping {destination.name}: origin resolves to the same graph node.")
                continue
            raise
    if not results:
        raise SystemExit("No routes were computed. Choose a different origin or destination.")

    export_route_outputs(graph, results, config, make_plot=not args.skip_plot)

    print(f"Graph source: {graph_source_label(graph)}")
    print(f"Origin: {origin.name}")
    print(f"Destination: {', '.join(destination.name for destination in destinations)}")
    print(f"Safety data: {safety_path}")
    print(f"Route summary CSV: {config.route_summary_csv_path}")
    print(f"Route summary Markdown: {config.route_summary_md_path}")
    print(f"Route GeoJSON: {config.route_geojson_path}")
    if not args.skip_plot:
        print(f"Route plot: {config.route_plot_path}")
    print("")
    for result in results:
        print(
            f"{result.route_type}: "
            f"{result.total_distance_m / 1000.0:.2f} km, "
            f"{result.estimated_travel_time_min:.1f} min, "
            f"mean risk {result.mean_risk_score:.3f}"
        )

    return 0


def resolve_origin(args: argparse.Namespace, config) -> object:
    """Resolve either a named origin or a custom lat/lon origin."""

    from zurich_safe_routing.config import Location

    if args.origin_lat is not None or args.origin_lon is not None:
        if args.origin_lat is None or args.origin_lon is None:
            raise SystemExit("Use --origin-lat and --origin-lon together.")
        return Location(args.origin_name, args.origin_lat, args.origin_lon)

    try:
        return config.example_locations[args.origin]
    except KeyError as exc:
        valid = ", ".join(sorted(config.example_locations))
        raise SystemExit(f"Unknown origin key {exc}. Valid keys: {valid}") from exc


def resolve_destinations(args: argparse.Namespace, config) -> list[object]:
    """Resolve one selected destination or both fixed campus destinations."""

    if args.destination == "both_campuses":
        return [config.example_locations[key] for key in config.campus_destination_keys]

    try:
        return [config.example_locations[args.destination]]
    except KeyError as exc:
        valid = ", ".join(sorted([*config.example_locations, "both_campuses"]))
        raise SystemExit(f"Unknown destination key {exc}. Valid keys: {valid}") from exc


if __name__ == "__main__":
    raise SystemExit(main())
