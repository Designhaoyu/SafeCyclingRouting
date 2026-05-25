"""Export route summaries, GeoJSON, and simple verification plots."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import networkx as nx

from .config import DEFAULT_CONFIG, RoutingConfig, ensure_project_directories
from .routing import RouteResult, results_to_dataframe


def export_route_outputs(
    graph: nx.MultiDiGraph,
    results: list[RouteResult],
    config: RoutingConfig = DEFAULT_CONFIG,
    *,
    make_plot: bool = True,
) -> None:
    """Write all Step 2 route comparison outputs."""

    ensure_project_directories(config)
    export_route_summary_csv(results, config.route_summary_csv_path)
    export_route_summary_markdown(results, config.route_summary_md_path)
    export_routes_geojson(graph, results, config.route_geojson_path)
    if make_plot:
        export_route_plot(graph, results, config.route_plot_path)


def export_route_summary_csv(results: list[RouteResult], output_path: Path) -> None:
    """Write route metrics as CSV."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    results_to_dataframe(results).to_csv(output_path, index=False)


def export_route_summary_markdown(results: list[RouteResult], output_path: Path) -> None:
    """Write route metrics plus a short interpretation as Markdown."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df = results_to_dataframe(results)
    lines = [
        "# Step 2 Route Summary",
        "",
        "This file compares route strategies produced by the Step 2 routing algorithm.",
        "Risk values come from the selected Step 1 edge safety file.",
        "",
        dataframe_to_markdown_table(df),
        "",
        "## Interpretation",
        "",
        route_interpretation(results),
        "",
    ]
    output_path.write_text("\n".join(lines), encoding="utf-8")


def route_interpretation(results: list[RouteResult]) -> str:
    """Create a compact explanation of how the strategies differ."""

    if not results:
        return "No routes were computed."

    grouped: dict[tuple[str, str], list[RouteResult]] = {}
    for result in results:
        grouped.setdefault((result.origin_name, result.destination_name), []).append(result)

    interpretations = []
    for (origin_name, destination_name), group in grouped.items():
        shortest = min(group, key=lambda result: result.total_distance_m)
        safest = min(group, key=lambda result: result.mean_risk_score)
        fastest = min(group, key=lambda result: result.estimated_travel_time_min)
        interpretations.append(
            f"From {origin_name} to {destination_name}, the shortest route is "
            f"`{shortest.route_type}` at {shortest.total_distance_m / 1000.0:.2f} km, "
            f"the fastest route is `{fastest.route_type}` at "
            f"{fastest.estimated_travel_time_min:.1f} minutes, and the lowest "
            f"mean-risk route is `{safest.route_type}` with mean risk "
            f"{safest.mean_risk_score:.3f}."
        )

    return (
        " ".join(interpretations)
        + " The balanced route trades some efficiency for lower risk by adding "
        "normalized risk exposure to the routing cost."
    )


def dataframe_to_markdown_table(df: Any) -> str:
    """Render a small DataFrame as a Markdown table without extra dependencies."""

    try:
        import pandas as pd
    except ImportError:  # pragma: no cover - pandas is already a project dependency.
        pd = None

    headers = [str(column) for column in df.columns]
    rows = [
        ["" if pd is not None and pd.isna(value) else str(value) for value in row]
        for row in df.to_numpy()
    ]
    table = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        table.append("| " + " | ".join(row) + " |")
    return "\n".join(table)


def export_routes_geojson(
    graph: nx.MultiDiGraph,
    results: list[RouteResult],
    output_path: Path,
) -> None:
    """Write route links as a GeoJSON FeatureCollection.

    Each feature is one graph edge/link in a computed route. This makes Step 3
    coloring by per-link risk_score straightforward.
    """

    output_path.parent.mkdir(parents=True, exist_ok=True)
    features = []
    for result in results:
        route_id = route_identifier(result)
        for edge_index, (u, v, key) in enumerate(result.edge_triplets):
            data = graph.edges[u, v, key]
            coordinates = edge_geometry_coordinates(graph, u, v, data)
            if len(coordinates) < 2:
                continue
            features.append(
                {
                    "type": "Feature",
                    "properties": link_properties(
                        result,
                        data,
                        u,
                        v,
                        key,
                        edge_index,
                        route_id,
                    ),
                    "geometry": {
                        "type": "LineString",
                        "coordinates": coordinates,
                    },
                }
            )

    geojson = {"type": "FeatureCollection", "features": features}
    output_path.write_text(json.dumps(geojson, indent=2), encoding="utf-8")


def link_properties(
    result: RouteResult,
    data: dict[str, Any],
    u: Any,
    v: Any,
    key: Any,
    edge_index: int,
    route_id: str,
) -> dict[str, Any]:
    """Return GeoJSON properties for one route link."""

    length_m = float(data.get("length", 0.0))
    travel_time_s = float(data.get("travel_time_s", 0.0))
    risk_score = float(data.get("risk_score", 0.0))
    safety_score = float(data.get("safety_score", 1.0 - risk_score))
    risk_cost = float(data.get("risk_cost", risk_score * length_m))

    return {
        "route_id": route_id,
        "route_type": result.route_type,
        "origin_name": result.origin_name,
        "destination_name": result.destination_name,
        "segment_index": edge_index,
        "route_number_of_edges": result.number_of_edges,
        "u": str(u),
        "v": str(v),
        "key": str(key),
        "edge_id": str(data.get("edge_id", f"{u}_{v}_{key}")),
        "highway": str(data.get("highway", "")),
        "length_m": round(length_m, 3),
        "travel_time_s": round(travel_time_s, 3),
        "travel_time_min": round(travel_time_s / 60.0, 4),
        "speed_kph": round(float(data.get("speed_kph", 0.0)), 3),
        "risk_score": round(risk_score, 6),
        "safety_score": round(safety_score, 6),
        "risk_cost": round(risk_cost, 6),
        "edge_weight_cost": round(float(data.get(result.weight_attribute, 0.0)), 6),
        "route_total_distance_km": round(result.total_distance_m / 1000.0, 3),
        "route_estimated_travel_time_min": round(result.estimated_travel_time_min, 2),
        "route_total_risk_exposure": round(result.total_risk_exposure, 2),
        "route_mean_risk_score": round(result.mean_risk_score, 4),
        "route_combined_cost": round(result.combined_cost, 4),
        "alpha": result.alpha,
        "beta": result.beta,
        "base_weight": result.base_weight,
    }


def route_identifier(result: RouteResult) -> str:
    """Stable readable identifier for grouping route links in Step 3."""

    origin = result.origin_name.lower().replace(" ", "_")
    destination = result.destination_name.lower().replace(" ", "_")
    return f"{origin}__{destination}__{result.route_type}"


def export_route_plot(
    graph: nx.MultiDiGraph,
    results: list[RouteResult],
    output_path: Path,
) -> None:
    """Write a simple static route plot for Step 2 verification."""

    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib is not installed; skipping route plot.")
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(9, 7))

    for u, v, _ in graph.edges(keys=True):
        if "x" not in graph.nodes[u] or "x" not in graph.nodes[v]:
            continue
        ax.plot(
            [float(graph.nodes[u]["x"]), float(graph.nodes[v]["x"])],
            [float(graph.nodes[u]["y"]), float(graph.nodes[v]["y"])],
            color="#c9ced6",
            linewidth=0.5,
            alpha=0.25,
            zorder=1,
        )

    colors = ["#1f77b4", "#d62728", "#2ca02c", "#9467bd", "#ff7f0e", "#17becf"]
    for index, result in enumerate(results):
        coords = route_coordinates(graph, result)
        if len(coords) < 2:
            continue
        xs = [coord[0] for coord in coords]
        ys = [coord[1] for coord in coords]
        ax.plot(
            xs,
            ys,
            color=colors[index % len(colors)],
            linewidth=2.4,
            alpha=0.85,
            label=result.route_type,
            zorder=3,
        )

    ax.set_title("Step 2 Current Query Cycling Routes")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.legend(loc="best", fontsize=8)
    ax.grid(True, linewidth=0.3, alpha=0.4)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def route_coordinates(graph: nx.MultiDiGraph, result: RouteResult) -> list[list[float]]:
    """Convert a route result to GeoJSON-style longitude/latitude coordinates."""

    coordinates: list[list[float]] = []
    for u, v, key in result.edge_triplets:
        data = graph.edges[u, v, key]
        edge_coordinates = edge_geometry_coordinates(graph, u, v, data)
        if not coordinates:
            coordinates.extend(edge_coordinates)
        else:
            coordinates.extend(edge_coordinates[1:])
    return coordinates


def edge_geometry_coordinates(
    graph: nx.MultiDiGraph,
    u: Any,
    v: Any,
    data: dict[str, Any],
) -> list[list[float]]:
    """Return edge coordinates from geometry if present, otherwise node endpoints."""

    if "geometry_coordinates" in data:
        return [[float(x), float(y)] for x, y in data["geometry_coordinates"]]

    geometry = data.get("geometry")
    if geometry is not None and hasattr(geometry, "coords"):
        coords = [[float(x), float(y)] for x, y in geometry.coords]
        return orient_coordinates(graph, u, v, coords)

    return [
        [float(graph.nodes[u]["x"]), float(graph.nodes[u]["y"])],
        [float(graph.nodes[v]["x"]), float(graph.nodes[v]["y"])],
    ]


def orient_coordinates(
    graph: nx.MultiDiGraph,
    u: Any,
    v: Any,
    coords: list[list[float]],
) -> list[list[float]]:
    """Orient geometry coordinates from u to v when possible."""

    if not coords:
        return [
            [float(graph.nodes[u]["x"]), float(graph.nodes[u]["y"])],
            [float(graph.nodes[v]["x"]), float(graph.nodes[v]["y"])],
        ]

    u_coord = [float(graph.nodes[u]["x"]), float(graph.nodes[u]["y"])]
    v_coord = [float(graph.nodes[v]["x"]), float(graph.nodes[v]["y"])]
    forward_error = coordinate_error(coords[0], u_coord) + coordinate_error(coords[-1], v_coord)
    reverse_error = coordinate_error(coords[-1], u_coord) + coordinate_error(coords[0], v_coord)
    return list(reversed(coords)) if reverse_error < forward_error else coords


def coordinate_error(a: list[float], b: list[float]) -> float:
    """Small helper for comparing lon/lat pairs."""

    return abs(a[0] - b[0]) + abs(a[1] - b[1])
