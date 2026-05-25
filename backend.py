"""Run the Step 2 safe cycling route pipeline end to end."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# --- UI / Rendering Dependencies ---
import geopandas as gpd
import pandas as pd
import folium
import branca.colormap as cm




from src.zurich_safe_routing.config import DEFAULT_CONFIG, ensure_project_directories
from src.zurich_safe_routing.exports import export_route_outputs
from src.zurich_safe_routing.graph_builder import build_or_load_graph, graph_source_label
from src.zurich_safe_routing.routing import compare_route_strategies, prepare_edge_weights
from src.zurich_safe_routing.safety_data import (
    attach_safety_scores_to_graph,
    load_safety_scores,
)

# cli command line functions

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Compute Step 2 safe cycling routes for Zurich."
    )
    parser.add_argument(
        "--origin",
        default="wiedikon",
        help="Origin key from config.example_locations. Ignored if lat/lon are provided."
    )
    parser.add_argument(
        "--origin-lat",
        type=float,
        default=None,
        help="Custom origin latitude."
    )
    parser.add_argument(
        "--origin-lon",
        type=float,
        default=None,
        help="Custom origin longitude."
    )
    parser.add_argument(
        "--origin-name",
        default="Custom origin",
        help="Readable name used when --origin-lat and --origin-lon are provided."
    )
    parser.add_argument(
        "--destination",
        default="both_campuses",
        help="Destination key from config.example_locations, or both_campuses."
    )
    parser.add_argument(
        "--time-period",
        default="8",
        help="Safety-score time period to use."
    )
    parser.add_argument(
        "--safety-file",
        type=Path,
        default=None,
        help="Optional Step 1 safety CSV."
    )
    parser.add_argument(
        "--use-synthetic-graph",
        action="store_true",
        help="Use the small built-in graph instead of downloading OSM data."
    )
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Ignore cached OSM graph and download a fresh one."
    )
    parser.add_argument(
        "--skip-plot",
        action="store_true",
        help="Skip writing results/step2_current_route_plot.png."
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
        raise SystemExit(f"Safety file not found: {safety_path}.")

    safety_df = load_safety_scores(safety_path, time_period=args.time_period)
    graph = attach_safety_scores_to_graph(graph, safety_df)
    graph = prepare_edge_weights(graph)

    results = []
    for destination in destinations:
        try:
            results.extend(compare_route_strategies(graph, origin, destination, config=config))
        except ValueError as exc:
            if "same graph node" in str(exc):
                continue
            raise
            
    if not results:
        raise SystemExit("No routes were computed.")

    export_route_outputs(graph, results, config, make_plot=not args.skip_plot)
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

# streamlit integration function

def run_routing_pipeline_from_ui(origin_lat: float, origin_lon: float, time_period: str, destination_key: str):
    """
    Wrapper function meant to be called directly by the Streamlit frontend.
    Returns a tuple of (geojson_path, csv_path).
    """
    config = DEFAULT_CONFIG
    ensure_project_directories(config)

    # Mock the argparse Namespace to reuse existing CLI logic seamlessly
    args = argparse.Namespace(
        origin=None,
        origin_lat=origin_lat,
        origin_lon=origin_lon,
        origin_name="Custom Origin",
        destination=destination_key, # Passed from the UI dropdown
        time_period=str(time_period),
        safety_file=None,
        use_synthetic_graph=False,
        force_download=False,
        skip_plot=True # Skip static matplotlib plots for Streamlit
    )

    try:
        origin = resolve_origin(args, config)
        destinations = resolve_destinations(args, config)
    except SystemExit as e:
        raise ValueError(str(e))

    graph = build_or_load_graph(
        config, force_download=args.force_download,
        use_synthetic_graph=args.use_synthetic_graph, allow_synthetic_fallback=True,
    )

    # Fallback safety path logic 
    safety_path = config.real_safety_path
    if not safety_path.exists():
        # Depending on your setup, you might want to call generate_mock_edge_safety_scores here
        raise ValueError(f"Safety file not found: {safety_path}. Ensure data generation is complete.")

    safety_df = load_safety_scores(safety_path, time_period=args.time_period)
    graph = attach_safety_scores_to_graph(graph, safety_df)
    graph = prepare_edge_weights(graph)

    results = []
    for destination in destinations:
        try:
            results.extend(compare_route_strategies(graph, origin, destination, config=config))
        except ValueError as exc:
            if "same graph node" in str(exc):
                continue 
            raise
            
    if not results:
        raise ValueError("No routes were computed. Origin and destination might be too close.")

    export_route_outputs(graph, results, config, make_plot=False)
    
    return config.route_geojson_path, config.route_summary_csv_path


def render_final_map(geojson_file, csv_file):
    """
    Reads the output files and renders the final map, highlighting the 
    Balanced Route as the primary recommendation.
    """
    gdf = gpd.read_file(geojson_file)
    summary_df = pd.read_csv(csv_file)
    
    # Determine the initial map center
    first_geom = gdf.iloc[0].geometry
    start_point = first_geom.coords[0] 
    map_center = [start_point[1], start_point[0]] 
    
    # Initialize the base map (Removed fixed zoom_start to allow auto-fitting later)
    m = folium.Map(location=map_center, tiles="cartodbdark_matter")
    
    # Risk color scale 
    risk_col = 'risk_score'
    if risk_col in gdf.columns:
        risk_cmap = cm.LinearColormap(
            colors=['#00FF00', '#ADFF2F', '#FFFF00', '#FFA500', '#FF0000'], 
            vmin=0.0, vmax=1.0, caption="Risk Level", text_color='white'
        )
        m.add_child(risk_cmap)
        get_color = lambda x: risk_cmap(x)

    else:
        print(f"Warning: Column '{risk_col}' not found in GeoJSON!")
        get_color = lambda x: "#39FF14" 

    # Use FeatureGroup to group routes for LayerControl
    route_groups = {}

    for idx, row in gdf.iterrows():
        route_type = str(row.get('route_type', '')).lower()
        route_name = str(row.get('route_type', f'Route {idx}')).title()
        
        # If this route group doesn't exist yet, create a new FeatureGroup
        if route_name not in route_groups:
            route_groups[route_name] = folium.FeatureGroup(name=route_name)
            m.add_child(route_groups[route_name])
            
        dash_style = "10, 10"
        line_weight = 5        
        line_opacity = 0.6     

        if "balanced" in route_type:
            dash_style = None  
            line_weight = 5
            line_opacity = 1.0 
            
        tooltip_html = "<br>".join([f"<b>{k}:</b> {v}" for k, v in row.drop('geometry').items()])
            
        # Draw this line on the specific FeatureGroup
        folium.GeoJson(
            row.geometry,
            style_function=lambda f, r_val=row.get(risk_col, 0), d=dash_style, w=line_weight, o=line_opacity: {
                "color": get_color(r_val),
                "weight": w,
                "opacity": o,
                "dashArray": d
            },
            tooltip=folium.Tooltip(tooltip_html)
        ).add_to(route_groups[route_name])


    # Prioritize the 'balanced' route for extracting start/end points; fallback to entire dataset
    balanced_gdf = gdf[gdf['route_type'].str.contains('balanced', case=False, na=False)]
    target_gdf = balanced_gdf if not balanced_gdf.empty else gdf

    if not target_gdf.empty:
        # First point of the first segment
        real_start = target_gdf.iloc[0].geometry.coords[0]
        # Last point of the last segment
        real_end = target_gdf.iloc[-1].geometry.coords[-1]

        # Add Start Logo
        folium.Marker(
            location=[real_start[1], real_start[0]], # Note: Folium requires [latitude, longitude]
            icon=folium.Icon(color="green", icon="play")
        ).add_to(m)

        # Add End Logo
        folium.Marker(
            location=[real_end[1], real_end[0]],
            icon=folium.Icon(color="red", icon="stop")
        ).add_to(m)

    # Fit map bounds to encompass all routes
    bounds = gdf.total_bounds  # Returns format: [min_lon, min_lat, max_lon, max_lat]
    m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])

    # Add layer control and save
    folium.LayerControl().add_to(m)
    m.save("recommended_route_map.html")
    print("Successfully generated map: recommended_route_map.html")
    
    return m


if __name__ == "__main__":
    raise SystemExit(main())
