"""Central configuration for the Step 2 routing pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Location:
    """Named latitude/longitude pair used by the routing pipeline."""

    name: str
    latitude: float
    longitude: float


@dataclass(frozen=True)
class RoutingConfig:
    """Paths and parameters shared across the Step 2 modules."""

    project_root: Path = PROJECT_ROOT
    place_name: str = "Zurich, Switzerland"
    osm_network_type: str = "bike"
    default_bike_speed_kph: float = 15.0

    data_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "data")
    raw_data_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "data" / "raw")
    processed_data_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "data" / "processed")
    results_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "results")

    graph_cache_path: Path = field(
        default_factory=lambda: PROJECT_ROOT / "data" / "raw" / "zurich_bike_graph.graphml"
    )
    real_safety_path: Path = field(
        default_factory=lambda: PROJECT_ROOT
        / "data"
        / "processed"
        / "zurich_hourly_edge_safety_score.csv"
    )
    route_summary_csv_path: Path = field(
        default_factory=lambda: PROJECT_ROOT / "results" / "step2_route_summary.csv"
    )
    route_summary_md_path: Path = field(
        default_factory=lambda: PROJECT_ROOT / "results" / "step2_route_summary.md"
    )
    route_geojson_path: Path = field(
        default_factory=lambda: PROJECT_ROOT / "results" / "step2_current_routes.geojson"
    )
    route_plot_path: Path = field(
        default_factory=lambda: PROJECT_ROOT / "results" / "step2_current_route_plot.png"
    )

    example_locations: dict[str, Location] = field(
        default_factory=lambda: {
            "eth_zentrum": Location("ETH Zentrum", 47.37643, 8.54808),
            "eth_hoenggerberg": Location("ETH Hoenggerberg", 47.40831, 8.50751),
            "zurich_hb": Location("Zurich HB", 47.37818, 8.54019),
            "wiedikon": Location("Wiedikon", 47.37139, 8.51680),
        }
    )
    campus_destination_keys: tuple[str, str] = ("eth_zentrum", "eth_hoenggerberg")

    highway_speed_kph: dict[str, float] = field(
        default_factory=lambda: {
            "cycleway": 17.0,
            "path": 14.0,
            "living_street": 12.0,
            "residential": 15.0,
            "service": 12.0,
            "unclassified": 14.0,
            "tertiary": 17.0,
            "secondary": 18.0,
            "primary": 20.0,
            "track": 12.0,
            "footway": 8.0,
            "steps": 4.0,
        }
    )


DEFAULT_CONFIG = RoutingConfig()


def ensure_project_directories(config: RoutingConfig = DEFAULT_CONFIG) -> None:
    """Create data and result directories used by the Step 2 pipeline."""

    for path in [
        config.raw_data_dir,
        config.processed_data_dir,
        config.results_dir,
        config.project_root / "docs",
    ]:
        path.mkdir(parents=True, exist_ok=True)
