import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

from backend import run_routing_pipeline_from_ui, render_final_map

st.set_page_config(
    page_title="ETH Zurich Safe Cycling Routing",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session state ─────────────────────────────────────────────────────────────
for k, v in [("orig_lat", 47.3769), ("orig_lon", 8.5417), ("calculation_successful", False)]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=DM+Mono:wght@300;400;500&display=swap');

:root {
    --bg:        #1c1c1e;
    --surface:   #242426;
    --surface2:  #2c2c2e;
    --border:    #3a3a3c;
    --accent:    #c8f135;
    --accent2:   #3bf0e4;
    --text:      #f0f0f0;
    --muted:     #8e8e93;
    --danger:    #ff453a;
    --font-sans: 'Space Grotesk', sans-serif;
    --font-mono: 'DM Mono', monospace;
}

/* ── Base ── */
html, body, .stApp {
    background-color: var(--bg) !important;
    color: var(--text) !important;
    font-family: var(--font-sans) !important;
}

/* ── Hide only footer and deploy button, keep sidebar toggle intact ── */
#MainMenu, footer, .stDeployButton { display: none !important; }

/* Keep Streamlit header visible but transparent so toggle button works */
header[data-testid="stHeader"] {
    background: transparent !important;
    border-bottom: none !important;
}

/* ── Main content padding ── */
.block-container {
    padding-top: 12px !important;
    padding-bottom: 40px !important;
    padding-left: 24px !important;
    padding-right: 24px !important;
    max-width: 100% !important;
}

/* ── Custom header bar ── */
.eth-header {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 14px 22px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 20px;
    position: relative;
}
.eth-title {
    font-size: 13px;
    font-weight: 700;
    letter-spacing: .1em;
    text-transform: uppercase;
    color: var(--text);
    text-align: center;
}
.eth-title b { color: var(--accent); }
.eth-badge {
    font-family: var(--font-mono);
    font-size: 10px;
    color: var(--muted);
    letter-spacing: .12em;
    position: absolute;
    right: 22px;
}

/* ── Sidebar — colour only, no structural overrides ── */
[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebarContent"] {
    padding: 24px 18px 40px 18px !important;
}
[data-testid="stSidebar"] * {
    font-family: var(--font-sans) !important;
}

/* ── Sidebar section labels ── */
.sb-label {
    font-family: var(--font-mono) !important;
    font-size: 9px;
    letter-spacing: .2em;
    text-transform: uppercase;
    color: var(--muted);
    display: block;
    margin-bottom: 8px;
    margin-top: 22px;
}

/* ── Coord badge ── */
.coord-badge {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 6px 10px;
    font-family: var(--font-mono);
    font-size: 11px;
    color: var(--accent2);
    margin-top: 8px;
    display: block;
    letter-spacing: .04em;
}

/* ── Divider ── */
hr {
    border: none !important;
    border-top: 1px solid var(--border) !important;
    margin: 20px 0 !important;
}

/* ── Selectbox ── */
[data-testid="stSelectbox"] > div > div {
    background: var(--surface2) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
    color: var(--text) !important;
    font-size: 13px !important;
}
[data-testid="stSelectbox"] > div > div:hover {
    border-color: var(--accent) !important;
}

/* ── Checkboxes ── */
[data-testid="stCheckbox"] label {
    font-size: 13px !important;
    color: var(--text) !important;
}

/* ── Primary button ── */
[data-testid="stButton"] > button[kind="primary"] {
    background: var(--accent) !important;
    color: #111 !important;
    border: none !important;
    border-radius: 6px !important;
    font-family: var(--font-mono) !important;
    font-size: 10px !important;
    letter-spacing: .15em !important;
    text-transform: uppercase !important;
    padding: 13px 20px !important;
    width: 100% !important;
    margin-top: 16px !important;
    transition: opacity .15s !important;
}
[data-testid="stButton"] > button[kind="primary"]:hover { opacity: .82 !important; }

/* ── Section head ── */
.section-head {
    font-family: var(--font-mono);
    font-size: 10px;
    letter-spacing: .18em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 10px;
}
.section-head::after {
    content: '';
    flex: 1;
    height: 1px;
    background: var(--border);
}

/* ── Map wrap ── */
.map-wrap {
    border: 1px solid var(--border);
    border-radius: 8px;
    overflow: hidden;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    background: var(--surface) !important;
    overflow: hidden !important;
}
[data-testid="stExpander"] summary {
    background: var(--surface) !important;
    color: var(--text) !important;
    font-family: var(--font-mono) !important;
    font-size: 10px !important;
    letter-spacing: .14em !important;
    text-transform: uppercase !important;
    padding: 14px 16px !important;
}
[data-testid="stExpander"] summary:hover { background: var(--surface2) !important; }
[data-testid="stExpander"] [data-testid="stExpanderDetails"] {
    background: var(--surface) !important;
    padding: 16px !important;
}

/* ── Alert ── */
[data-testid="stAlert"] {
    background: rgba(255,69,58,.08) !important;
    border: 1px solid var(--danger) !important;
    border-radius: 6px !important;
    color: var(--danger) !important;
    font-family: var(--font-mono) !important;
    font-size: 11px !important;
}

/* ── Caption ── */
kbd, 
[data-testid="stSidebarCollapseButton"] span {
    display: none !important;
}

[data-testid="stSidebarCollapseButton"] svg {
    opacity: 0 !important;
}

[data-testid="stSidebarCollapseButton"] {
    position: relative !important;
}

[data-testid="stSidebarCollapseButton"]::after {
    content: "✕" !important;
    font-size: 16px !important;
    color: var(--text) !important;
    position: absolute !important;
    top: 50% !important;
    left: 50% !important;
    transform: translate(-50%, -50%) !important;
    font-family: var(--font-sans) !important;
    pointer-events: none !important; 
}
            
[data-testid="stCaptionContainer"] p {
    color: var(--muted) !important;
    font-family: var(--font-mono) !important;
    font-size: 11px !important;
}
            
div[data-testid="stVerticalBlock"] > div:has(.eth-header),
div.element-container:has(.eth-header) {
    position: sticky !important;
    top: 12px !important; 
    z-index: 999 !important;
    background-color: var(--bg); 
    padding-bottom: 5px; 
}
            
</style>
""", unsafe_allow_html=True)

# ── Header (in normal document flow, centred) ─────────────────────────────────
st.markdown("""
<div class="eth-header">
  <div class="eth-title">ETH Zürich&nbsp;<b>/</b>&nbsp;Safe Cycling Routing</div>
  <div class="eth-badge">Zürich · CH</div>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════
with st.sidebar:

    # ── 01 Origin ──────────────────────────────────────────────────────────
    st.markdown('<span class="sb-label">01 — Origin</span>', unsafe_allow_html=True)
    st.caption("Click the map to set your start point")

    m_picker = folium.Map(
        location=[47.3769, 8.5417],
        zoom_start=12,
        tiles="CartoDB dark_matter",
        attr=" ",
        zoom_control=True,
        scrollWheelZoom=True,
        dragging=True
    )
    m_picker.options["attributionControl"] = False

    folium.Marker(
        [st.session_state.orig_lat, st.session_state.orig_lon],
        icon=folium.Icon(color="green", icon="play", prefix="fa"),
    ).add_to(m_picker)

    picker_res = st_folium(
        m_picker,
        use_container_width=True,
        height=210,
        key="orig_picker",
        returned_objects=["last_clicked"],
    )
    if picker_res and picker_res.get("last_clicked"):
        nlat = picker_res["last_clicked"]["lat"]
        nlng = picker_res["last_clicked"]["lng"]
        if nlat != st.session_state.orig_lat or nlng != st.session_state.orig_lon:
            st.session_state.orig_lat = nlat
            st.session_state.orig_lon = nlng
            st.rerun()

    st.markdown(
        f'<div class="coord-badge">↗ {st.session_state.orig_lat:.4f}, {st.session_state.orig_lon:.4f}</div>',
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # ── 02 Destination ─────────────────────────────────────────────────────
    st.markdown('<span class="sb-label">02 — Destination</span>', unsafe_allow_html=True)
    dest_options = {
        "ETH Zentrum":     "eth_zentrum",
        "ETH Hönggerberg": "eth_hoenggerberg",
    }
    dest_choice = st.selectbox(
        "Campus", list(dest_options.keys()), label_visibility="collapsed"
    )
    selected_dest_key = dest_options[dest_choice]

    st.markdown("---")

    # ── 03 Departure Hour ──────────────────────────────────────────────────
    st.markdown('<span class="sb-label">03 — Departure Hour</span>', unsafe_allow_html=True)
    time_options = [str(i) for i in range(24)]
    selected_time = st.selectbox(
        "Hour (0–23)", time_options, index=0, label_visibility="collapsed"
    )

    st.markdown("---")

    # ── 04 Visible Routes ──────────────────────────────────────────────────
    st.markdown('<span class="sb-label">04 — Visible Routes</span>', unsafe_allow_html=True)
    show_balanced = st.checkbox("Balanced  (recommended)", value=True)
    show_safest   = st.checkbox("Safest",   value=True)
    show_shortest = st.checkbox("Shortest", value=True)
    show_fastest  = st.checkbox("Fastest",  value=True)

    visible_routes_dict = {
        "balanced": show_balanced,
        "safest":   show_safest,
        "shortest": show_shortest,
        "fastest":  show_fastest,
    }

    calculate_btn = st.button(
        "→  Generate Routes", type="primary", use_container_width=True
    )

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN — Routing
# ═══════════════════════════════════════════════════════════════════════════════
if calculate_btn:
    with st.spinner(f"Computing optimised routes to {dest_choice}…"):
        try:
            geojson_path, csv_path = run_routing_pipeline_from_ui(
                origin_lat=st.session_state.orig_lat,
                origin_lon=st.session_state.orig_lon,
                time_period=selected_time,
                destination_key=selected_dest_key,
            )
            st.session_state["saved_geojson"] = geojson_path
            st.session_state["saved_csv"]     = csv_path
            st.session_state["calculation_successful"] = True
        except Exception as e:
            st.error(f"Routing error: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN — Results
# ═══════════════════════════════════════════════════════════════════════════════
if st.session_state.get("calculation_successful", False):

    current_geojson = st.session_state["saved_geojson"]
    current_csv     = st.session_state["saved_csv"]

    m = render_final_map(
        geojson_file=current_geojson,
        csv_file=current_csv
    )

    st.markdown(
        f'<div class="section-head">Route Map — {dest_choice}</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="map-wrap">', unsafe_allow_html=True)
    st_folium(m, use_container_width=True, height=600, returned_objects=[])
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    summary_df = pd.read_csv(current_csv)
    mask = summary_df["route_type"].str.lower().apply(
        lambda x: any(k in x for k, v in visible_routes_dict.items() if v)
    )
    with st.expander("📊  Route Summary", expanded=False):
        st.dataframe(summary_df[mask], hide_index=True, use_container_width=True)

else:
    st.markdown("""
    <div style="display:flex;flex-direction:column;align-items:center;
                justify-content:center;height:60vh;gap:14px;opacity:.3;">
      <div style="font-size:48px;">🚲</div>
      <div style="font-family:'DM Mono',monospace;font-size:10px;
                  letter-spacing:.22em;text-transform:uppercase;color:#f0f0f0;">
        Configure your route in the sidebar
      </div>
    </div>
    """, unsafe_allow_html=True)