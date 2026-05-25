"""Route computation and comparison for Step 2."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import networkx as nx
import pandas as pd

from .config import DEFAULT_CONFIG, Location, RoutingConfig
from .graph_builder import nearest_node


@dataclass
class RouteStrategy:
    """Definition of one route objective."""

    name: str
    weight_attribute: str
    alpha: float | None = None
    beta: float | None = None
    base_weight: str | None = None


@dataclass
class RouteResult:
    """Metrics and path information for one computed route."""

    route_type: str
    origin_name: str
    destination_name: str
    origin_node: Any
    destination_node: Any
    path_nodes: list[Any]
    edge_triplets: list[tuple[Any, Any, Any]]
    weight_attribute: str
    number_of_edges: int
    total_distance_m: float
    estimated_travel_time_min: float
    total_risk_exposure: float
    mean_risk_score: float
    combined_cost: float
    alpha: float | None = None
    beta: float | None = None
    base_weight: str | None = None

    def to_summary_dict(self) -> dict[str, Any]:
        """Return report-friendly values for CSV and Markdown exports."""

        data = asdict(self)
        data.pop("path_nodes")
        data.pop("edge_triplets")
        data["total_distance_km"] = round(self.total_distance_m / 1000.0, 3)
        data["estimated_travel_time_min"] = round(self.estimated_travel_time_min, 2)
        data["total_risk_exposure"] = round(self.total_risk_exposure, 2)
        data["mean_risk_score"] = round(self.mean_risk_score, 4)
        data["combined_cost"] = round(self.combined_cost, 4)
        data.pop("total_distance_m")
        return data


def prepare_edge_weights(graph: nx.MultiDiGraph) -> nx.MultiDiGraph:
    """Create routing weight attributes used by all route strategies."""

    required = ["length", "travel_time_s", "risk_score", "risk_cost"]
    for attribute in required:
        if any(attribute not in data for _, _, _, data in graph.edges(keys=True, data=True)):
            raise ValueError(
                f"Graph edges are missing {attribute!r}. Build the graph and attach "
                "safety scores before computing routes."
            )

    normalize_edge_attribute(graph, "length", "length_norm")
    normalize_edge_attribute(graph, "travel_time_s", "travel_time_norm")
    normalize_edge_attribute(graph, "risk_cost", "risk_cost_norm")

    for _, _, _, data in graph.edges(keys=True, data=True):
        data["weight_distance"] = float(data["length"])
        data["weight_time"] = float(data["travel_time_s"])
        data["weight_safety"] = float(data["risk_cost"])

    return graph


def add_balanced_weight(
    graph: nx.MultiDiGraph,
    *,
    alpha: float,
    beta: float,
    base_weight: str = "time",
) -> str:
    """Add and return a combined edge weight attribute.

    alpha controls efficiency and beta controls safety. The two components are
    normalized to comparable 0-1 edge-level ranges before being combined.
    """

    if alpha < 0 or beta < 0:
        raise ValueError("alpha and beta must be non-negative.")
    if alpha == 0 and beta == 0:
        raise ValueError("At least one of alpha or beta must be positive.")

    base_attribute = {
        "distance": "length_norm",
        "time": "travel_time_norm",
    }.get(base_weight)
    if base_attribute is None:
        raise ValueError("base_weight must be either 'distance' or 'time'.")

    name = balanced_weight_name(alpha, beta, base_weight)
    total = alpha + beta
    normalized_alpha = alpha / total
    normalized_beta = beta / total

    for _, _, _, data in graph.edges(keys=True, data=True):
        data[name] = (
            normalized_alpha * float(data[base_attribute])
            + normalized_beta * float(data["risk_cost_norm"])
        )

    return name


def default_route_strategies(graph: nx.MultiDiGraph) -> list[RouteStrategy]:
    """Create the required Step 2 route strategies."""

    return [
        RouteStrategy("shortest_distance", "weight_distance"),
        RouteStrategy("fastest_time", "weight_time"),
        RouteStrategy("safest_route", "weight_safety"),
        RouteStrategy(
            "balanced_route",
            add_balanced_weight(graph, alpha=0.5, beta=0.5, base_weight="time"),
            alpha=0.5,
            beta=0.5,
            base_weight="time",
        ),
    ]


def compare_route_strategies(
    graph: nx.MultiDiGraph,
    origin: Location,
    destination: Location,
    strategies: list[RouteStrategy] | None = None,
    config: RoutingConfig = DEFAULT_CONFIG,
) -> list[RouteResult]:
    """Compute and summarize several routes between two named locations."""

    del config
    origin_node = nearest_node(graph, origin)
    destination_node = nearest_node(graph, destination)

    if origin_node == destination_node:
        raise ValueError("Origin and destination resolve to the same graph node.")

    strategies = strategies or default_route_strategies(graph)
    results: list[RouteResult] = []

    for strategy in strategies:
        results.append(
            compute_route(
                graph,
                origin,
                destination,
                origin_node,
                destination_node,
                strategy,
            )
        )

    return results


def compute_route(
    graph: nx.MultiDiGraph,
    origin: Location,
    destination: Location,
    origin_node: Any,
    destination_node: Any,
    strategy: RouteStrategy,
) -> RouteResult:
    """Compute one weighted shortest path and summarize its metrics."""

    try:
        path_nodes = nx.shortest_path(
            graph,
            source=origin_node,
            target=destination_node,
            weight=strategy.weight_attribute,
        )
    except nx.NetworkXNoPath as exc:
        raise RuntimeError(
            f"No route found from {origin.name} to {destination.name} "
            f"using strategy {strategy.name}."
        ) from exc
    except nx.NodeNotFound as exc:
        raise ValueError(
            f"Invalid origin or destination node for strategy {strategy.name}."
        ) from exc

    edge_triplets = choose_route_edges(graph, path_nodes, strategy.weight_attribute)
    edge_data = [graph.edges[u, v, key] for u, v, key in edge_triplets]

    total_distance_m = sum(float(data["length"]) for data in edge_data)
    total_time_s = sum(float(data["travel_time_s"]) for data in edge_data)
    total_risk_exposure = sum(float(data["risk_cost"]) for data in edge_data)
    combined_cost = sum(float(data[strategy.weight_attribute]) for data in edge_data)
    mean_risk_score = total_risk_exposure / total_distance_m if total_distance_m else 0.0

    return RouteResult(
        route_type=strategy.name,
        origin_name=origin.name,
        destination_name=destination.name,
        origin_node=origin_node,
        destination_node=destination_node,
        path_nodes=list(path_nodes),
        edge_triplets=edge_triplets,
        weight_attribute=strategy.weight_attribute,
        number_of_edges=len(edge_triplets),
        total_distance_m=total_distance_m,
        estimated_travel_time_min=total_time_s / 60.0,
        total_risk_exposure=total_risk_exposure,
        mean_risk_score=mean_risk_score,
        combined_cost=combined_cost,
        alpha=strategy.alpha,
        beta=strategy.beta,
        base_weight=strategy.base_weight,
    )


def choose_route_edges(
    graph: nx.MultiDiGraph,
    path_nodes: list[Any],
    weight_attribute: str,
) -> list[tuple[Any, Any, Any]]:
    """Pick the concrete edge key used between each pair of path nodes."""

    edge_triplets: list[tuple[Any, Any, Any]] = []
    for u, v in zip(path_nodes[:-1], path_nodes[1:]):
        candidates = graph.get_edge_data(u, v)
        if not candidates:
            raise RuntimeError(f"Path contains missing edge from {u!r} to {v!r}.")
        best_key = min(
            candidates,
            key=lambda key: float(candidates[key].get(weight_attribute, float("inf"))),
        )
        edge_triplets.append((u, v, best_key))
    return edge_triplets


def normalize_edge_attribute(
    graph: nx.MultiDiGraph,
    source_attribute: str,
    target_attribute: str,
) -> None:
    """Min-max normalize an edge attribute onto 0-1."""

    values = [
        float(data[source_attribute])
        for _, _, _, data in graph.edges(keys=True, data=True)
        if source_attribute in data
    ]
    if not values:
        raise ValueError(f"No edge values found for {source_attribute!r}.")

    minimum = min(values)
    maximum = max(values)
    spread = maximum - minimum

    for _, _, _, data in graph.edges(keys=True, data=True):
        value = float(data[source_attribute])
        data[target_attribute] = 0.0 if spread == 0 else (value - minimum) / spread


def results_to_dataframe(results: list[RouteResult]) -> pd.DataFrame:
    """Convert route results to a tidy summary DataFrame."""

    return pd.DataFrame([result.to_summary_dict() for result in results])


def balanced_weight_name(alpha: float, beta: float, base_weight: str) -> str:
    """Return a valid graph attribute name for a balanced routing weight."""

    alpha_label = str(alpha).replace(".", "_")
    beta_label = str(beta).replace(".", "_")
    return f"weight_balanced_{base_weight}_alpha_{alpha_label}_beta_{beta_label}"
