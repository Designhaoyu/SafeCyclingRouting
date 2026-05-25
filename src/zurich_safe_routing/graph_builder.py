"""Build, load, and prepare the cycling graph used by Step 2 routing."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import networkx as nx

from .config import DEFAULT_CONFIG, Location, RoutingConfig, ensure_project_directories

try:
    import osmnx as ox
except ImportError:  # pragma: no cover - exercised only when osmnx is not installed.
    ox = None


Coordinate = tuple[float, float]


def build_or_load_graph(
    config: RoutingConfig = DEFAULT_CONFIG,
    *,
    force_download: bool = False,
    use_synthetic_graph: bool = False,
    allow_synthetic_fallback: bool = True,
) -> nx.MultiDiGraph:
    """Return a Zurich cycling graph with length and travel-time attributes.

    The preferred source is OpenStreetMap through OSMnx. A small synthetic
    graph is available for development and for environments where the OSM
    download fails.
    """

    ensure_project_directories(config)

    if use_synthetic_graph:
        graph = build_synthetic_zurich_graph(config)
        return ensure_edge_lengths_and_times(graph, config)

    if ox is None:
        if allow_synthetic_fallback:
            print("OSMnx is not installed. Falling back to the synthetic Zurich graph.")
            graph = build_synthetic_zurich_graph(config)
            return ensure_edge_lengths_and_times(graph, config)
        raise ImportError(
            "OSMnx is required to download the Zurich bike network. "
            "Install dependencies with: pip install -r requirements.txt"
        )

    if config.graph_cache_path.exists() and not force_download:
        graph = ox.load_graphml(config.graph_cache_path)
    else:
        try:
            graph = ox.graph_from_place(
                config.place_name,
                network_type=config.osm_network_type,
                simplify=True,
            )
            ox.save_graphml(graph, filepath=config.graph_cache_path)
        except Exception as exc:
            if not allow_synthetic_fallback:
                raise RuntimeError(
                    f"Could not download OSM graph for {config.place_name!r}."
                ) from exc
            print(
                "Could not download the OSM graph. Falling back to the synthetic "
                f"Zurich graph. Original error: {exc}"
            )
            graph = build_synthetic_zurich_graph(config)

    return ensure_edge_lengths_and_times(graph, config)


def ensure_edge_lengths_and_times(
    graph: nx.MultiDiGraph,
    config: RoutingConfig = DEFAULT_CONFIG,
) -> nx.MultiDiGraph:
    """Ensure each edge has length in meters, speed, and travel time."""

    for u, v, key, data in graph.edges(keys=True, data=True):
        if "length" not in data or data["length"] in (None, ""):
            data["length"] = haversine_distance_m(
                (float(graph.nodes[u]["y"]), float(graph.nodes[u]["x"])),
                (float(graph.nodes[v]["y"]), float(graph.nodes[v]["x"])),
            )

        length_m = float(data["length"])
        highway = first_value(data.get("highway", "residential"))
        speed_kph = float(data.get("speed_kph") or speed_for_highway(highway, config))
        travel_time_s = length_m / (speed_kph * 1000.0 / 3600.0)

        data["length"] = length_m
        data["highway"] = highway
        data["speed_kph"] = speed_kph
        data["travel_time_s"] = travel_time_s
        data["edge_id"] = edge_identifier(u, v, key)

    return graph


def build_synthetic_zurich_graph(config: RoutingConfig = DEFAULT_CONFIG) -> nx.MultiDiGraph:
    """Create a deterministic Zurich-like bike graph for offline testing."""

    graph = nx.MultiDiGraph()
    graph.graph["name"] = "synthetic_zurich_bike_graph"
    graph.graph["crs"] = "EPSG:4326"

    nodes: dict[str, Coordinate] = {
        "eth_zentrum": (47.37643, 8.54808),
        "central": (47.37688, 8.54320),
        "zurich_hb": (47.37818, 8.54019),
        "limmatquai": (47.37195, 8.54375),
        "buerkliplatz": (47.36621, 8.54183),
        "paradeplatz": (47.36988, 8.53802),
        "sihlcity": (47.35725, 8.52241),
        "wiedikon": (47.37139, 8.51680),
        "hardbruecke": (47.38509, 8.51766),
        "escher_wyss": (47.39068, 8.52117),
        "wipkingen": (47.39350, 8.52770),
        "bucheggplatz": (47.39558, 8.53735),
        "schaffhauserplatz": (47.39252, 8.53828),
        "irchel": (47.39857, 8.55046),
        "oberstrass": (47.38690, 8.55004),
        "fluntern": (47.38292, 8.56063),
        "hoengg": (47.40418, 8.49781),
        "eth_hoenggerberg": (47.40831, 8.50751),
        "affoltern": (47.41808, 8.50852),
    }

    for node_id, (lat, lon) in nodes.items():
        graph.add_node(node_id, y=lat, x=lon)

    edges = [
        ("eth_zentrum", "central", "tertiary", 1.10),
        ("central", "zurich_hb", "secondary", 1.05),
        ("zurich_hb", "hardbruecke", "primary", 1.20),
        ("hardbruecke", "escher_wyss", "secondary", 1.05),
        ("escher_wyss", "wipkingen", "tertiary", 1.08),
        ("wipkingen", "hoengg", "residential", 1.28),
        ("hoengg", "eth_hoenggerberg", "cycleway", 1.15),
        ("eth_zentrum", "oberstrass", "residential", 1.10),
        ("oberstrass", "schaffhauserplatz", "tertiary", 1.05),
        ("schaffhauserplatz", "bucheggplatz", "secondary", 1.08),
        ("bucheggplatz", "wipkingen", "secondary", 1.12),
        ("bucheggplatz", "irchel", "path", 1.20),
        ("irchel", "affoltern", "cycleway", 1.25),
        ("affoltern", "eth_hoenggerberg", "cycleway", 1.10),
        ("eth_zentrum", "fluntern", "residential", 1.20),
        ("fluntern", "irchel", "cycleway", 1.25),
        ("central", "limmatquai", "primary", 1.05),
        ("limmatquai", "buerkliplatz", "secondary", 1.08),
        ("buerkliplatz", "paradeplatz", "secondary", 1.00),
        ("paradeplatz", "wiedikon", "tertiary", 1.15),
        ("wiedikon", "hardbruecke", "residential", 1.30),
        ("sihlcity", "wiedikon", "cycleway", 1.10),
        ("buerkliplatz", "sihlcity", "cycleway", 1.25),
        ("hardbruecke", "wipkingen", "residential", 1.12),
        ("schaffhauserplatz", "wipkingen", "residential", 1.08),
        ("central", "oberstrass", "residential", 1.12),
    ]

    for u, v, highway, factor in edges:
        add_bidirectional_synthetic_edge(graph, u, v, highway, factor, config)

    return graph


def add_bidirectional_synthetic_edge(
    graph: nx.MultiDiGraph,
    u: str,
    v: str,
    highway: str,
    detour_factor: float,
    config: RoutingConfig,
) -> None:
    """Add a two-way synthetic edge with approximate geometry and length."""

    u_coord = (float(graph.nodes[u]["y"]), float(graph.nodes[u]["x"]))
    v_coord = (float(graph.nodes[v]["y"]), float(graph.nodes[v]["x"]))
    length_m = haversine_distance_m(u_coord, v_coord) * detour_factor
    geometry = [
        [float(graph.nodes[u]["x"]), float(graph.nodes[u]["y"])],
        [float(graph.nodes[v]["x"]), float(graph.nodes[v]["y"])],
    ]
    speed_kph = speed_for_highway(highway, config)
    attrs = {
        "length": length_m,
        "highway": highway,
        "speed_kph": speed_kph,
        "travel_time_s": length_m / (speed_kph * 1000.0 / 3600.0),
        "geometry_coordinates": geometry,
    }
    graph.add_edge(u, v, **attrs)
    graph.add_edge(v, u, **{**attrs, "geometry_coordinates": list(reversed(geometry))})


def nearest_node(graph: nx.MultiDiGraph, location: Location) -> Any:
    """Find the graph node closest to a named latitude/longitude location."""

    if ox is not None and graph.graph.get("crs") == "EPSG:4326":
        try:
            return ox.distance.nearest_nodes(graph, X=location.longitude, Y=location.latitude)
        except (TypeError, ValueError):
            # Synthetic test graphs use readable string node ids, while OSMnx's
            # nearest-node helper expects ids it can cast to integers.
            pass

    target = (location.latitude, location.longitude)
    best_node = None
    best_distance = math.inf
    for node, data in graph.nodes(data=True):
        if "x" not in data or "y" not in data:
            continue
        distance = haversine_distance_m(target, (float(data["y"]), float(data["x"])))
        if distance < best_distance:
            best_node = node
            best_distance = distance
    if best_node is None:
        raise ValueError("Could not find a nearest node because graph nodes lack x/y coordinates.")
    return best_node


def edge_identifier(u: Any, v: Any, key: Any) -> str:
    """Stable edge identifier used to join Step 1 safety data to graph edges."""

    return f"{u}_{v}_{key}"


def first_value(value: Any) -> str:
    """Return a single string from an OSM attribute that may be a list."""

    if isinstance(value, list):
        return str(value[0]) if value else "residential"
    return str(value)


def speed_for_highway(highway: str, config: RoutingConfig = DEFAULT_CONFIG) -> float:
    """Estimate cycling speed in km/h from the OSM highway category."""

    return config.highway_speed_kph.get(highway, config.default_bike_speed_kph)


def haversine_distance_m(start: Coordinate, end: Coordinate) -> float:
    """Compute great-circle distance between two lat/lon points in meters."""

    lat1, lon1 = start
    lat2, lon2 = end
    radius_m = 6_371_000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    return 2.0 * radius_m * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def graph_source_label(graph: nx.MultiDiGraph) -> str:
    """Human-readable label for reports."""

    name = str(graph.graph.get("name", "")).lower()
    if "synthetic" in name:
        return "synthetic"
    return "openstreetmap"


def graph_cache_exists(path: Path) -> bool:
    """Small wrapper used by docs/tests to check whether OSM data was cached."""

    return path.exists()
