import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# Import backend wrapper and map renderer
from backend import run_routing_pipeline_from_ui, render_final_map

st.set_page_config(page_title="ETH Zurich Safe Cycling Routing", layout="wide")

st.title("🚲 ETH Zurich Safe Cycling Routing Application")

# Initialize session state for map clicking coordinates
if "orig_lat" not in st.session_state:
    st.session_state.orig_lat = 47.3769
    st.session_state.orig_lon = 8.5417

# --- UI Setup ---
with st.sidebar:
    st.header("📍 1. Choose Origin")
    st.markdown("Click on the map below to set your starting point:")
    
    # Generate a mini-map specifically for users to click and select their origin
    m_picker = folium.Map(location=[47.3769, 8.5417], zoom_start=12)
    folium.Marker(
        [st.session_state.orig_lat, st.session_state.orig_lon], 
        icon=folium.Icon(color="green", icon="play", prefix="fa")
    ).add_to(m_picker)
    
    # Capture user clicks on the mini-map
    picker_res = st_folium(m_picker, width=300, height=250, key="orig_picker")
    if picker_res and picker_res.get("last_clicked"):
        new_lat = picker_res["last_clicked"]["lat"]
        new_lng = picker_res["last_clicked"]["lng"]
        # If coordinates change, update session state and force page rerun
        if new_lat != st.session_state.orig_lat or new_lng != st.session_state.orig_lon:
            st.session_state.orig_lat = new_lat
            st.session_state.orig_lon = new_lng
            st.rerun()

    st.caption(f"Selected Origin: {st.session_state.orig_lat:.4f}, {st.session_state.orig_lon:.4f}")
    
    st.markdown("---")
    
    st.header("🏁 2. Select Destination")
    # Dictionary mapping for the two ETH campuses
    dest_options = {
        "ETH Zentrum": "eth_zentrum", 
        "ETH Hönggerberg": "eth_hoenggerberg"
    }
    dest_choice = st.selectbox("Campus:", list(dest_options.keys()))
    selected_dest_key = dest_options[dest_choice]

    st.markdown("---")
    
    st.header("⏳ 3. Departure Time")
    # Ensure hours 0-23 are all generated as options
    time_options = ["all_day", "morning_rush_hour"] + [str(i) for i in range(24)]
    selected_time = st.selectbox("Time Period:", time_options, index=0)
    
    st.markdown("---")
    
    # Route Layer visibility toggle controls
    st.header("👁️ 4. Display Options")
    show_balanced = st.checkbox("🟢 Balanced Route (Recommended)", value=True)
    show_safest = st.checkbox("🛡️ Safest Route", value=True)
    show_shortest = st.checkbox("📏 Shortest Route", value=True)
    show_fastest = st.checkbox("⏱️ Fastest Route", value=True)
    
    visible_routes_dict = {
        "balanced": show_balanced,
        "safest": show_safest,
        "shortest": show_shortest,
        "fastest": show_fastest
    }

    calculate_btn = st.button("🗺️ Generate Safe Routes", type="primary", use_container_width=True)


# Execution Flow
if calculate_btn:
    with st.spinner(f"Computing optimized routes to {dest_choice}..."):
        try:
            # Pass the newly added selected_dest_key argument
            geojson_path, csv_path = run_routing_pipeline_from_ui(
                origin_lat=st.session_state.orig_lat, 
                origin_lon=st.session_state.orig_lon, 
                time_period=selected_time,
                destination_key=selected_dest_key
            )
            
            st.session_state['saved_geojson'] = geojson_path
            st.session_state['saved_csv'] = csv_path
            st.session_state['calculation_successful'] = True
            
        except Exception as e:
            st.error(f"An error occurred during routing: {e}")

# Render results
if st.session_state.get('calculation_successful', False):
    
    current_geojson = st.session_state['saved_geojson']
    current_csv = st.session_state['saved_csv']
    
    # Pass the visibility toggle dictionary to the mapping function
    m = render_final_map(
        geojson_file=current_geojson, 
        csv_file=current_csv, 
        visible_routes=visible_routes_dict
    )
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader(f"Routes to {dest_choice}")
        st_folium(m, width=900, height=600, returned_objects=[])
        
    with col2:
        st.subheader("Route Summary")
        summary_df = pd.read_csv(current_csv)
        
        # Dynamically filter table display based on checked status
        # Convert route names in the table to lowercase for robust comparison
        mask = summary_df['route_type'].str.lower().apply(
            lambda x: any(k in x for k, v in visible_routes_dict.items() if v)
        )
        filtered_df = summary_df[mask]
        st.dataframe(filtered_df, hide_index=True)
        
    