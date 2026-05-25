"""Step 1 safety data loading and graph attachment utilities."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import networkx as nx
import pandas as pd

from .graph_builder import edge_identifier


REQUIRED_EDGE_ID_COLUMNS = {"u", "v", "key", "edge_id"}


def load_safety_scores(path: Path, *, time_period: str = "8") -> pd.DataFrame:
    """Load Step 1-style safety scores from CSV and validate the schema.

    time_period is matched flexibly so hourly Step 1 data can use values such
    as 8, "8", "08", "8.0", "h08", "hour_08", or "08:00".
    """

    if not path.exists():
        raise FileNotFoundError(
            f"Safety score file not found: {path}. "
            "Provide the real Step 1 CSV with the expected columns."
        )

    safety_df = pd.read_csv(path)
    missing_columns = REQUIRED_EDGE_ID_COLUMNS - set(safety_df.columns)
    if missing_columns:
        raise ValueError(
            f"Safety score file is missing required columns: {sorted(missing_columns)}"
        )
    if "risk_score" not in safety_df.columns and "safety_score" not in safety_df.columns:
        raise ValueError(
            "Safety score file must contain at least one of: risk_score, safety_score."
        )
    if "risk_score" not in safety_df.columns:
        safety_df["risk_score"] = 1.0 - pd.to_numeric(safety_df["safety_score"])
    if "safety_score" not in safety_df.columns:
        safety_df["safety_score"] = 1.0 - pd.to_numeric(safety_df["risk_score"])

    safety_df["risk_score"] = pd.to_numeric(safety_df["risk_score"])
    safety_df["safety_score"] = pd.to_numeric(safety_df["safety_score"])

    if "time_period" in safety_df.columns:
        requested_period = normalize_time_period(time_period)
        available_periods = safety_df["time_period"].dropna()
        period_keys = safety_df["time_period"].map(normalize_time_period)
        filtered = safety_df[period_keys == requested_period].copy()
        if filtered.empty:
            raise ValueError(
                f"No safety rows found for time_period={time_period!r}. "
                f"Available periods: {format_available_time_periods(available_periods)}"
            )
        safety_df = filtered

    return safety_df


def normalize_time_period(value: Any) -> str:
    """Normalize labels and hourly time periods for robust CSV filtering."""

    if pd.isna(value):
        return ""

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if float(value).is_integer():
            return str(int(value))
        return str(value).strip().lower()

    text = str(value).strip().lower()
    if not text:
        return ""

    numeric_text = text
    if numeric_text.startswith("hour_"):
        numeric_text = numeric_text.removeprefix("hour_")
    elif numeric_text.startswith("hour-"):
        numeric_text = numeric_text.removeprefix("hour-")
    elif numeric_text.startswith("h"):
        numeric_text = numeric_text.removeprefix("h")

    hour_match = re.fullmatch(r"0*(\d{1,2})(?:\.0+)?", numeric_text)
    if hour_match:
        return str(int(hour_match.group(1)))

    clock_match = re.fullmatch(r"0*(\d{1,2}):(?:00|0)(?::(?:00|0))?", numeric_text)
    if clock_match:
        return str(int(clock_match.group(1)))

    return text


def format_available_time_periods(values: pd.Series) -> list[str]:
    """Return compact original and normalized time-period labels for errors."""

    periods: list[str] = []
    seen: set[str] = set()
    for value in values:
        original = str(value)
        normalized = normalize_time_period(value)
        label = original if original == normalized else f"{original} -> {normalized}"
        if label not in seen:
            periods.append(label)
            seen.add(label)
    return sorted(periods)


def attach_safety_scores_to_graph(
    graph: nx.MultiDiGraph,
    safety_df: pd.DataFrame,
    *,
    default_risk_score: float = 0.5,
) -> nx.MultiDiGraph:
    """Attach risk and safety scores to graph edges using u/v/key or edge_id."""

    safety_by_triplet = {
        (str(row.u), str(row.v), str(row.key)): row
        for row in safety_df.itertuples(index=False)
    }
    safety_by_edge_id = {str(row.edge_id): row for row in safety_df.itertuples(index=False)}

    missing_count = 0
    for u, v, key, data in graph.edges(keys=True, data=True):
        row = safety_by_triplet.get((str(u), str(v), str(key)))
        if row is None:
            row = safety_by_edge_id.get(str(data.get("edge_id", edge_identifier(u, v, key))))

        if row is None:
            risk_score = default_risk_score
            safety_score = 1.0 - default_risk_score
            missing_count += 1
        else:
            risk_score = float(row.risk_score)
            safety_score = float(row.safety_score)

        data["risk_score"] = risk_score
        data["safety_score"] = safety_score
        data["risk_cost"] = risk_score * float(data.get("length", 1.0))

    graph.graph["safety_scores_missing_edges"] = missing_count
    return graph
