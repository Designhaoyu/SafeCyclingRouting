import argparse
import sys
from pathlib import Path
import geopandas as gpd
import pandas as pd
import folium
import branca.colormap as cm

# 1. Original Project Setup Imports
PROJECT_ROOT = Path(__file__).resolve().parent  
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from zurich_safe_routing.config import DEFAULT_CONFIG, ensure_project_directories
from zurich_safe_routing.exports import export_route_outputs
from zurich_safe_routing.graph_builder import build_or_load_graph, graph_source_label
from zurich_safe_routing.routing import compare_route_strategies, prepare_edge_weights
from zurich_safe_routing.safety_data import (
    attach_safety_scores_to_graph,
    generate_mock_edge_safety_scores,
    load_safety_scores,
)
from zurich_safe_routing.config import Location

def resolve_origin(args: argparse.Namespace, config) -> object:
    """Original resolve_origin function (Unmodified)"""
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
    """Original resolve_destinations function (Unmodified)"""
    if args.destination == "both_campuses":
        return [config.example_locations[key] for key in config.campus_destination_keys]
    try:
        return [config.example_locations[args.destination]]
    except KeyError as exc:
        valid = ", ".join(sorted([*config.example_locations, "both_campuses"]))
        raise SystemExit(f"Unknown destination key {exc}. Valid keys: {valid}") from exc

# --- 2. The Wrapper Function for Streamlit ---
def run_routing_pipeline_from_ui(origin_lat: float, origin_lon: float, time_period: str, destination_key: str):
    """
    Modification: Added destination_key parameter to dynamically select the campus destination.
    """
    args = argparse.Namespace(
        origin="wiedikon",
        origin_lat=origin_lat,
        origin_lon=origin_lon,
        origin_name="Custom Origin",
        destination=destination_key,  # Receive campus selection from frontend
        time_period=str(time_period),
        safety_file=None,
        use_synthetic_graph=False,
        force_download=False,
        regenerate_mock_safety=False, # Set to True if missing hourly data (e.g., hours 1-7) in the mock CSV
        skip_plot=True 
    )
    
    config = DEFAULT_CONFIG
    ensure_project_directories(config)

    origin = resolve_origin(args, config)
    destinations = resolve_destinations(args, config)

    graph = build_or_load_graph(
        config, force_download=args.force_download,
        use_synthetic_graph=args.use_synthetic_graph, allow_synthetic_fallback=True,
    )

    safety_path = args.safety_file or config.mock_safety_path
    if args.regenerate_mock_safety or (args.safety_file is None and not safety_path.exists()):
        generate_mock_edge_safety_scores(graph, safety_path, config)

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
        raise ValueError("No routes were computed. Choose a different origin.")

    export_route_outputs(graph, results, config, make_plot=not args.skip_plot)
    return config.route_geojson_path, config.route_summary_csv_path


# --- 3. Our Map Render Function ---
def render_final_map(geojson_file, csv_file, visible_routes=None):
    """
    Modifications:
    1. Receives 'visible_routes' dictionary to control which lines to render.
    2. Adds custom oversized markers for origin (green play) and destination (red flag).
    """
    if visible_routes is None:
        visible_routes = {"balanced": True, "safest": True, "shortest": True, "fastest": True}

    gdf = gpd.read_file(geojson_file)
    first_geom = gdf.iloc[0].geometry
    map_center = [first_geom.coords[0][1], first_geom.coords[0][0]] 
    m = folium.Map(location=map_center, zoom_start=14, tiles="cartodbdark_matter")
    
    risk_col = 'accident_count_current' if 'accident_count_current' in gdf.columns else 'accident_count_50m'
    if risk_col in gdf.columns:
        max_risk = max(gdf[risk_col].max(), 5)
        risk_cmap = cm.LinearColormap(['#00FF00', '#ADFF2F', '#FFFF00', '#FFA500', '#FF0000'], vmin=0, vmax=max_risk)
        m.add_child(risk_cmap)
        get_color = lambda x: risk_cmap(x)
    else:
        get_color = lambda x: "#39FF14"

    # Add: Extract origin and destination coordinates, place highlighted Markers
    if not gdf.empty:
        start_coord = gdf.iloc[0].geometry.coords[0]
        end_coord = gdf.iloc[0].geometry.coords[-1]
        
        folium.Marker(
            location=[start_coord[1], start_coord[0]], popup="📍 Origin",
            icon=folium.Icon(color="green", icon="play", prefix="fa")
        ).add_to(m)
        
        folium.Marker(
            location=[end_coord[1], end_coord[0]], popup="🏁 Destination",
            icon=folium.Icon(color="red", icon="flag", prefix="fa")
        ).add_to(m)

    # Draw routes iterating through the GeoDataFrame
    for idx, row in gdf.iterrows():
        route_type = str(row.get('route_type', '')).lower()
        
        # Core: Layer filtering control! Skip drawing this line if the user unchecked it in the UI
        if "balanced" in route_type and not visible_routes.get("balanced"): continue
        if "safest" in route_type and not visible_routes.get("safest"): continue
        if "shortest" in route_type and not visible_routes.get("shortest"): continue
        if "fastest" in route_type and not visible_routes.get("fastest"): continue

        dash_style, line_weight, line_opacity = "10, 10", 5, 0.6 
        if "balanced" in route_type:
            dash_style, line_weight, line_opacity = None, 8, 1.0 
            
        tooltip_html = "<br>".join([f"<b>{k}:</b> {v}" for k, v in row.drop('geometry').items()])
        folium.GeoJson(
            row.geometry, name=row.get('route_type', f'Route {idx}'),
            style_function=lambda f, r=row.get(risk_col, 0), d=dash_style, w=line_weight, o=line_opacity: {
                "color": get_color(r), "weight": w, "opacity": o, "dashArray": d
            },
            tooltip=folium.Tooltip(tooltip_html)
        ).add_to(m)

    folium.LayerControl().add_to(m)
    return m