"""Shared authenticated CARTO Dark Matter tile configuration."""
import os
from pathlib import Path
from urllib.parse import quote
import toml


def carto_tile_options():
    key = os.environ.get("CARTO_BASEMAP_API_KEY", "").strip()
    if not key:
        path = Path(__file__).resolve().parents[2] / ".streamlit" / "secrets.toml"
        if path.exists():
            key = str(toml.load(path).get("CARTO_BASEMAP_API_KEY", "")).strip()
    if not key:
        import streamlit as st
        try:
            key = str(st.secrets["CARTO_BASEMAP_API_KEY"]).strip()
        except (KeyError, FileNotFoundError):
            pass
    if not key:
        return {"tiles": "OpenStreetMap"}
    return {
        "tiles": "https://basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}.png?key=" + quote(key, safe=""),
        "attr": '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        "max_zoom": 20,
    }
