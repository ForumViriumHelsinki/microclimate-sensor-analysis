"""
Streamlit app for comparing temperature and humidity measurements from two sensors.

Features:
- Map with sensor locations
- Comparison plot of two sensors
- Time series plot of two sensors
- FMI weather station data overlay

Metadata example from  geojson:

    {
      "type": "Feature",
      "properties": {
        "id": "24E124136E106661",
        "project": "KYMP",
        "installationDate": "2024-06-16T00:00:00",
        "street": "Rautalammintie 1",
        "postalcode": "00550",
        "city": "Helsinki",
        "district": "Vallila",
        "sunExposure": 1.0,
        "solarShielding": 1.0,
        "heightFromGround": 3.0,
        "mountingType": "metal pole",
        "terrain": "flat",
        "groundCover": "grass/50, stone pavement/50",
        "landUse": null,
        "buildingDensity": null,
        "LCZ": null,
        "LCZ long": null,
        "Kuvaus": "avoimella kentällä",
        "fid": 4.0,
        "Tyyppi": "Auringossa",
        "Huomiot": "Tolppa parkkialueella",
        "Kiinnitystapa": "Tolppa",
        "Sensori": 6661.0,
        "measurement": {
          "time": "2025-09-13T08:42:32.506000+03:00",
          "humidity": 89.5,
          "temperature": 16.199999999999999
        }
      },
      "geometry": {
        "type": "Point",
        "coordinates": [
          24.95566158371556,
          60.196418390653328
        ]
      }
    },


"""

import json
from datetime import timedelta

import folium
import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_folium import st_folium


@st.cache_data
def load_sensor_data():
    """Load hourly resampled sensor data"""
    return pd.read_parquet("/app/data/interim/data_1h.parquet")


@st.cache_data
def load_fmi_data():
    """Load FMI weather station data"""
    return pd.read_parquet("/app/data/interim/fmi_1h.parquet")


@st.cache_data
def load_sensor_metadata():
    """Load sensor locations and metadata from GeoJSON"""
    with open("/app/data/interim/data_latest.geojson", "r") as f:
        geojson_data = json.load(f)

    sensors = []
    for feature in geojson_data["features"]:
        props = feature["properties"]
        sensor_info = {
            "id": props["id"],
            "name": props.get("name", ""),
            "tyyppi": props.get("Tyyppi", ""),
            "numero": props.get("Numero", ""),
            "street": props.get("street", ""),
            "district": props.get("district", ""),
            "huomiot": props.get("Huomiot", ""),
            "kuvaus": props.get("Kuvaus", ""),
            "mounting_type": props.get("mountingType", ""),
            "height_from_ground": props.get("heightFromGround", ""),
            "ground_cover": props.get("groundCover", ""),
            "sun_exposure": props.get("sunExposure", ""),
            "installation_date": props.get("installationDate", ""),
            "lat": feature["geometry"]["coordinates"][1],
            "lon": feature["geometry"]["coordinates"][0],
            "current_temp": props["measurement"]["temperature"] if "measurement" in props else None,
            "current_humidity": props["measurement"]["humidity"] if "measurement" in props else None,
            "measurement_time": props["measurement"]["time"] if "measurement" in props else None,
        }
        sensors.append(sensor_info)

    return pd.DataFrame(sensors)


def create_sensor_map(sensor_df):
    """Create Folium map with sensor locations"""
    # Calculate map center
    center_lat = sensor_df["lat"].mean()
    center_lon = sensor_df["lon"].mean()

    # Create base map
    m = folium.Map(location=[center_lat, center_lon], zoom_start=10, tiles="OpenStreetMap")

    # Add sensors to map
    for _, sensor in sensor_df.iterrows():
        # Color based on sensor type or current temperature
        if sensor["tyyppi"] == "Auringossa":
            color = "red"
            icon_color = "white"
        elif sensor["tyyppi"] == "Varjossa":
            color = "blue"
            icon_color = "white"
        else:
            color = "gray"
            icon_color = "white"

        # Format sensor ID with bold last 4 digits
        sensor_id = sensor["id"]
        if len(sensor_id) >= 4:
            formatted_id = sensor_id[:-4] + f"<b>{sensor_id[-4:]}</b>"
        else:
            formatted_id = f"<b>{sensor_id}</b>"

        # Format measurement time and values
        measurement_line = ""
        if sensor["measurement_time"] and sensor["current_temp"] is not None:
            from datetime import datetime

            try:
                # Parse ISO timestamp and format to Finnish time
                dt = datetime.fromisoformat(sensor["measurement_time"].replace("Z", "+00:00"))
                time_str = dt.strftime("%d.%m. %H:%M")
                measurement_line = f"{time_str} • {sensor['current_temp']:.1f}°C • {sensor['current_humidity']:.1f}%"
            except (ValueError, TypeError):
                measurement_line = f"{sensor['current_temp']:.1f}°C • {sensor['current_humidity']:.1f}%"

        # Format location (district, street)
        location_parts = []
        if sensor["district"]:
            location_parts.append(sensor["district"])
        if sensor["street"]:
            location_parts.append(sensor["street"])
        location_line = ", ".join(location_parts) if location_parts else "N/A"

        # Format secondary info on one line
        secondary_info = []
        if sensor["mounting_type"]:
            secondary_info.append(f"Mount: {sensor['mounting_type']}")
        if sensor["height_from_ground"]:
            secondary_info.append(f"Height: {sensor['height_from_ground']}m")
        if sensor["ground_cover"]:
            secondary_info.append(f"Ground cover: {sensor['ground_cover']}")
        if sensor["sun_exposure"] is not None:
            secondary_info.append(f"Sun exposure: {sensor['sun_exposure']}")

        secondary_line = " • ".join(secondary_info) if secondary_info else ""

        # Create popup text
        popup_text = f"""
        <div style="font-family: Arial, sans-serif; font-size: 13px; min-width: 280px; line-height: 1.4;">
            <div style="font-size: 14px; margin-bottom: 8px;">{formatted_id}</div>
            <div style="margin-bottom: 6px; color: #2E8B57; font-weight: 500;">{measurement_line}</div>
            <div style="margin-bottom: 8px;">{location_line}</div>
            {f'<div style="font-size: 11px; color: #666; margin-bottom: 6px;">{secondary_line}</div>' if secondary_line else ""}
            {f'<div style="font-size: 11px; color: #666; font-style: italic;">{sensor["kuvaus"]}</div>' if sensor.get("kuvaus") else ""}
            {f'<div style="font-size: 11px; color: #888; margin-top: 4px;">Notes: {sensor["huomiot"]}</div>' if sensor.get("huomiot") else ""}
            <div style="margin-top: 10px; font-size: 11px; color: #999; font-style: italic;">Click to select for comparison</div>
        </div>
        """

        # Create tooltip text
        tooltip_text = f"{sensor['id']} - {sensor['current_temp']:.1f}°C"

        folium.Marker(
            location=[sensor["lat"], sensor["lon"]],
            popup=folium.Popup(popup_text, max_width=300),
            tooltip=tooltip_text,
            icon=folium.Icon(color=color, icon="thermometer-half", prefix="fa", icon_color=icon_color),
        ).add_to(m)

    return m


def create_comparison_plot(df, sensor1_id, sensor2_id, measurement_type, start_date, end_date):
    """Create scatter plot comparing two sensors"""
    # Convert dates to datetime with timezone
    start_datetime = pd.to_datetime(start_date).tz_localize("UTC")
    end_datetime = pd.to_datetime(end_date).tz_localize("UTC") + timedelta(days=1)

    # Filter data for selected sensors and time period
    data1 = df[(df["dev-id"] == sensor1_id) & (df.index >= start_datetime) & (df.index <= end_datetime)]
    data2 = df[(df["dev-id"] == sensor2_id) & (df.index >= start_datetime) & (df.index <= end_datetime)]

    # Create merged dataset for scatter plot
    merged_data = pd.DataFrame(
        {
            f"{measurement_type}_sensor1": data1[measurement_type],
            f"{measurement_type}_sensor2": data2[measurement_type],
        }
    ).dropna()

    if merged_data.empty:
        return None, None

    # Add time information for visualization
    merged_data["timestamp"] = merged_data.index.strftime("%Y-%m-%d %H:%M")
    merged_data["hour"] = merged_data.index.hour

    # Create scatter plot
    fig = px.scatter(
        merged_data,
        x=f"{measurement_type}_sensor1",
        y=f"{measurement_type}_sensor2",
        color="hour",
        color_continuous_scale=[
            [0.0, "darkblue"],  # 00:00
            [0.25, "skyblue"],  # 06:00
            [0.5, "yellow"],  # 12:00
            [0.75, "orange"],  # 18:00
            [1.0, "darkblue"],  # 24:00
        ],
        labels={
            f"{measurement_type}_sensor1": f"{sensor1_id} {measurement_type}",
            f"{measurement_type}_sensor2": f"{sensor2_id} {measurement_type}",
            "hour": "Time of day",
        },
        title=f"Comparison of hourly average {measurement_type} measurements",
        hover_data=["timestamp"],
    )

    # Update colorbar
    fig.update_coloraxes(
        colorbar_ticktext=["00:00", "06:00", "12:00", "18:00", "24:00"], colorbar_tickvals=[0, 6, 12, 18, 24]
    )

    # Calculate common axis range based on both sensors' data
    min_val = min(merged_data[f"{measurement_type}_sensor1"].min(), merged_data[f"{measurement_type}_sensor2"].min())
    max_val = max(merged_data[f"{measurement_type}_sensor1"].max(), merged_data[f"{measurement_type}_sensor2"].max())

    # Add some padding (5% on each side)
    padding = (max_val - min_val) * 0.05
    axis_min = min_val - padding
    axis_max = max_val + padding

    # Set 1:1 aspect ratio and equal axis ranges
    fig.update_layout(
        width=600,
        height=600,
        xaxis=dict(range=[axis_min, axis_max], constrain="domain", showgrid=True, gridwidth=1, gridcolor="lightgray"),
        yaxis=dict(
            range=[axis_min, axis_max],
            scaleanchor="x",
            scaleratio=1,
            constrain="domain",
            showgrid=True,
            gridwidth=1,
            gridcolor="lightgray",
        ),
    )

    # Explicitly update axis ranges again to ensure they stick
    fig.update_xaxes(range=[axis_min, axis_max])
    fig.update_yaxes(range=[axis_min, axis_max])

    # Add identity line using the axis range
    fig.add_scatter(
        x=[axis_min, axis_max],
        y=[axis_min, axis_max],
        mode="lines",
        name="Identity line",
        line=dict(dash="dash", color="gray"),
    )

    return fig, merged_data


def create_timeseries_plot(
    df, sensor1_id, sensor2_id, measurement_type, start_date, end_date, fmi_station=None, fmi_measurements=None
):
    """Create time series plot showing temperature curves for selected sensors with optional FMI overlay"""
    # Convert dates to datetime with timezone
    start_datetime = pd.to_datetime(start_date).tz_localize("UTC")
    end_datetime = pd.to_datetime(end_date).tz_localize("UTC") + timedelta(days=1)

    # Filter data for selected sensors and time period
    data1 = df[(df["dev-id"] == sensor1_id) & (df.index >= start_datetime) & (df.index <= end_datetime)]
    data2 = df[(df["dev-id"] == sensor2_id) & (df.index >= start_datetime) & (df.index <= end_datetime)]

    if data1.empty and data2.empty:
        return None

    # Create time series plot
    fig = px.line(
        title=f"{measurement_type.capitalize()} time series comparison",
        labels={
            "index": "Time",
            "value": f"{measurement_type.capitalize()} ({'°C' if measurement_type == 'temperature' else '%'})",
        },
    )

    # Get FMI data first to determine if we need secondary axis
    fmi_data = None
    fmi_filtered = None
    has_secondary_axis = False

    if fmi_station and fmi_station != "None" and fmi_measurements:
        fmi_data = load_fmi_data()
        fmi_filtered = fmi_data[
            (fmi_data["Station"] == fmi_station)
            & (fmi_data.index >= start_datetime)
            & (fmi_data.index <= end_datetime)
        ]
        has_secondary_axis = any(m in ["Cloud amount", "Precipitation amount"] for m in fmi_measurements)

    # LAYER 1 (Background): Add cloud amount first (furthest back)
    if fmi_filtered is not None and not fmi_filtered.empty:
        if "Cloud amount" in fmi_measurements and "Cloud amount" in fmi_filtered.columns:
            if not fmi_filtered["Cloud amount"].isna().all():
                fig.add_bar(
                    x=fmi_filtered.index,
                    y=fmi_filtered["Cloud amount"],
                    name="FMI Cloud amount",
                    marker_color="lightblue",
                    opacity=0.4,
                    yaxis="y2",
                    hovertemplate="<b>%{fullData.name}</b><br>"
                    + "Time: %{x}<br>"
                    + "Cloud amount: %{y:.1f} oktas<br>"
                    + "<extra></extra>",
                )

    # LAYER 2: Add precipitation amount (on top of cloud amount)
    if fmi_filtered is not None and not fmi_filtered.empty:
        if "Precipitation amount" in fmi_measurements and "Precipitation amount" in fmi_filtered.columns:
            if not fmi_filtered["Precipitation amount"].isna().all():
                fig.add_bar(
                    x=fmi_filtered.index,
                    y=fmi_filtered["Precipitation amount"],
                    name="FMI Precipitation amount",
                    marker_color="lightgreen",
                    opacity=0.6,
                    yaxis="y2",
                    hovertemplate="<b>%{fullData.name}</b><br>"
                    + "Time: %{x}<br>"
                    + "Precipitation: %{y:.1f} mm<br>"
                    + "<extra></extra>",
                )

    # LAYER 3: Add FMI temperature/humidity lines
    if fmi_filtered is not None and not fmi_filtered.empty:
        if "Air temperature" in fmi_measurements and "Air temperature" in fmi_filtered.columns:
            if not fmi_filtered["Air temperature"].isna().all():
                fig.add_scatter(
                    x=fmi_filtered.index,
                    y=fmi_filtered["Air temperature"],
                    mode="lines",
                    name="FMI Air temperature",
                    line=dict(color="green", width=2, dash="dash"),
                    yaxis="y",
                    hovertemplate="<b>%{fullData.name}</b><br>"
                    + "Time: %{x}<br>"
                    + "Temperature: %{y:.1f}°C<br>"
                    + "<extra></extra>",
                )

        if "Relative humidity" in fmi_measurements and "Relative humidity" in fmi_filtered.columns:
            if not fmi_filtered["Relative humidity"].isna().all():
                fig.add_scatter(
                    x=fmi_filtered.index,
                    y=fmi_filtered["Relative humidity"],
                    mode="lines",
                    name="FMI Relative humidity",
                    line=dict(color="green", width=2, dash="dash"),
                    yaxis="y",
                    hovertemplate="<b>%{fullData.name}</b><br>"
                    + "Time: %{x}<br>"
                    + "Humidity: %{y:.1f}%<br>"
                    + "<extra></extra>",
                )

    # LAYER 4 & 5 (Foreground): Add sensor data last (on top)
    if not data1.empty:
        fig.add_scatter(
            x=data1.index,
            y=data1[measurement_type],
            mode="lines",
            name=f"Sensor 1: {sensor1_id}",
            line=dict(color="red", width=2),
            hovertemplate="<b>%{fullData.name}</b><br>"
            + "Time: %{x}<br>"
            + f"{measurement_type.capitalize()}: "
            + "%{y:.1f}"
            + ("°C" if measurement_type == "temperature" else "%")
            + "<br>"
            + "<extra></extra>",
        )

    if not data2.empty:
        fig.add_scatter(
            x=data2.index,
            y=data2[measurement_type],
            mode="lines",
            name=f"Sensor 2: {sensor2_id}",
            line=dict(color="blue", width=2),
            hovertemplate="<b>%{fullData.name}</b><br>"
            + "Time: %{x}<br>"
            + f"{measurement_type.capitalize()}: "
            + "%{y:.1f}"
            + ("°C" if measurement_type == "temperature" else "%")
            + "<br>"
            + "<extra></extra>",
        )

    # Update layout with improved zoom and selection
    fig.update_layout(
        width=800,
        height=600,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor="lightgray",
            rangeslider=dict(visible=True),  # Add range slider for easier navigation
            type="date",
        ),
        yaxis=dict(showgrid=True, gridwidth=1, gridcolor="lightgray"),
        # Preserve UI state across updates
        uirevision="timeseries",
        # Add selection tools
        dragmode="zoom",
        # Improve hover behavior
        hovermode="x unified",
    )

    # Configure secondary y-axis if needed
    if has_secondary_axis:
        fig.update_layout(
            yaxis2=dict(
                title="Cloud amount (oktas) / Precipitation (mm)", overlaying="y", side="right", showgrid=False
            )
        )

    return fig


def update_date_range_from_selection(selected_points, sensor_data):
    """Update date range based on selected data points"""
    if not selected_points or "range" not in selected_points:
        return None, None

    # Extract time range from selection
    x_range = selected_points["range"]["x"]
    if len(x_range) >= 2:
        start_time = pd.to_datetime(x_range[0])
        end_time = pd.to_datetime(x_range[1])
        return start_time, end_time

    return None, None


def main():
    st.set_page_config(page_title="Sensor Map Comparison", layout="wide")

    st.title("🌡️ Interactive Sensor Data Comparison")
    st.markdown("Select sensors from the map below to compare their measurements")

    # Load data
    sensor_data = load_sensor_data()
    sensor_metadata = load_sensor_metadata()

    # Get available sensor IDs
    available_sensors = sorted(sensor_metadata["id"].unique())

    # Initialize session state for date range synchronization
    if "zoom_start_date" not in st.session_state:
        st.session_state.zoom_start_date = None
    if "zoom_end_date" not in st.session_state:
        st.session_state.zoom_end_date = None

    # Sidebar for controls
    with st.sidebar:
        st.header("🎯 Sensor Selection")

        # Initialize session state for sensor selection
        if "selected_sensor1" not in st.session_state:
            st.session_state.selected_sensor1 = available_sensors[0]
        if "selected_sensor2" not in st.session_state:
            st.session_state.selected_sensor2 = (
                available_sensors[1] if len(available_sensors) > 1 else available_sensors[0]
            )

        # Manual sensor selection
        sensor1 = st.selectbox(
            "First sensor",
            available_sensors,
            index=available_sensors.index(st.session_state.selected_sensor1),
            key="sensor1_select",
        )

        sensor2 = st.selectbox(
            "Second sensor",
            available_sensors,
            index=available_sensors.index(st.session_state.selected_sensor2),
            key="sensor2_select",
        )

        # Update session state
        st.session_state.selected_sensor1 = sensor1
        st.session_state.selected_sensor2 = sensor2

        # Measurement type selection
        measurement_type = st.selectbox("Measurement type", ["temperature", "humidity"])

        # FMI weather station selection
        st.header("🌦️ FMI Weather Station")

        # Load FMI data to get available stations
        fmi_data = load_fmi_data()
        available_stations = ["None"] + sorted(fmi_data["Station"].unique().tolist())

        # Initialize session state for FMI station
        if "selected_fmi_station" not in st.session_state:
            st.session_state.selected_fmi_station = "None"

        selected_fmi_station = st.selectbox(
            "Compare with FMI station",
            available_stations,
            index=available_stations.index(st.session_state.selected_fmi_station),
            key="fmi_station_select",
            help="Select a weather station to overlay FMI data on the time series plot",
        )

        # Update session state
        st.session_state.selected_fmi_station = selected_fmi_station

        if selected_fmi_station != "None":
            # FMI measurement selection
            fmi_measurements = st.multiselect(
                "FMI measurements to show",
                ["Air temperature", "Relative humidity", "Cloud amount", "Precipitation amount"],
                default=["Air temperature"] if measurement_type == "temperature" else ["Relative humidity"],
                help="Select which FMI measurements to display as overlay",
            )
            st.session_state.selected_fmi_measurements = fmi_measurements
        else:
            st.session_state.selected_fmi_measurements = []

        # Date range selection
        st.header("📅 Time Period")

        # Use zoomed dates if available, otherwise use default range
        default_start = (
            st.session_state.zoom_start_date.date()
            if st.session_state.zoom_start_date is not None
            else sensor_data.index.min().date()
        )
        default_end = (
            st.session_state.zoom_end_date.date()
            if st.session_state.zoom_end_date is not None
            else sensor_data.index.max().date()
        )

        start_date = st.date_input("Start date", default_start)
        end_date = st.date_input("End date", default_end)

        # Add button to reset zoom
        if st.session_state.zoom_start_date is not None:
            if st.button("🔄 Reset to full range"):
                st.session_state.zoom_start_date = None
                st.session_state.zoom_end_date = None
                st.rerun()

        # Display selected sensor info
        st.header("📊 Selected Sensors")
        if sensor1 in sensor_metadata["id"].values and sensor2 in sensor_metadata["id"].values:
            sensor1_info = sensor_metadata[sensor_metadata["id"] == sensor1].iloc[0]
            sensor2_info = sensor_metadata[sensor_metadata["id"] == sensor2].iloc[0]

            st.markdown(f"**🔴 Sensor 1:** {sensor1}")
            st.caption(f"Type: {sensor1_info['tyyppi']} | Temp: {sensor1_info['current_temp']:.1f}°C")

            st.markdown(f"**🔵 Sensor 2:** {sensor2}")
            st.caption(f"Type: {sensor2_info['tyyppi']} | Temp: {sensor2_info['current_temp']:.1f}°C")

    # Main content area with map and visualizations
    # Create and display map
    st.subheader("📍 Sensor Locations")

    # Display map information about clicking
    if sensor1 != sensor2:
        st.info("💡 Click on sensors in the map to quickly select them using the buttons that appear below")

    sensor_map = create_sensor_map(sensor_metadata)
    map_data = st_folium(
        sensor_map,
        width=None,
        height=500,
        returned_objects=["last_object_clicked", "last_clicked"],
        key="sensor_map",
    )

    # Get clicked sensor information and show selection buttons
    clicked_sensor = None
    if map_data["last_object_clicked"]:
        clicked_lat = map_data["last_object_clicked"]["lat"]
        clicked_lon = map_data["last_object_clicked"]["lng"]

        # Find the closest sensor to the clicked location
        distances = ((sensor_metadata["lat"] - clicked_lat) ** 2 + (sensor_metadata["lon"] - clicked_lon) ** 2) ** 0.5
        closest_idx = distances.idxmin()
        clicked_sensor = sensor_metadata.iloc[closest_idx]["id"]

    # Show sensor selection buttons when a sensor is clicked
    if clicked_sensor:
        st.success(f"📍 Selected sensor from map: **{clicked_sensor}**")

        col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])

        with col_btn1:
            if st.button("🔴 Set as Sensor 1", use_container_width=True, help="Use this sensor as Sensor 1"):
                st.session_state.selected_sensor1 = clicked_sensor
                st.rerun()

        with col_btn2:
            if st.button("🔵 Set as Sensor 2", use_container_width=True, help="Use this sensor as Sensor 2"):
                st.session_state.selected_sensor2 = clicked_sensor
                st.rerun()

    # Create comparison visualizations
    st.subheader("📈 Sensor Comparison")

    # Add explanation about UTC time usage in visualizations
    st.info(
        "ℹ️ **Time Reference**: All visualizations use UTC time for physical consistency. "
        "In Helsinki, solar noon occurs at approximately 10:20 UTC (13:20 summer time, 12:20 winter time). "
        "This ensures that measurements taken at the same solar position appear with consistent colors in scatter plots."
    )

    if sensor1 != sensor2:
        # Create tabs for different visualizations
        tab1, tab2 = st.tabs(["📈 Time Series", "📊 Scatter Plot"])

        with tab1:
            # Time series plot
            ts_fig = create_timeseries_plot(
                sensor_data,
                sensor1,
                sensor2,
                measurement_type,
                start_date,
                end_date,
                fmi_station=st.session_state.get("selected_fmi_station", "None"),
                fmi_measurements=st.session_state.get("selected_fmi_measurements", []),
            )

            if ts_fig is not None:
                st.info(
                    "💡 Use the Quick Time Range Selection buttons below or adjust the Time Period in the sidebar to filter data. The scatter plot will update accordingly."
                )

                # Display the chart with standard plotly chart
                st.plotly_chart(ts_fig, use_container_width=True, key="main_timeseries")

                # Note about zoom functionality
                st.info(
                    "🔍 **Zoom Tip**: After zooming in the chart above, use the Quick Time Range Selection buttons below to set similar time ranges for both charts."
                )

                # Add manual time range controls
                st.subheader("⏱️ Quick Time Range Selection")
                col1, col2, col3, col4, col5, col6 = st.columns(6)

                with col1:
                    if st.button("📅 Last 7 days"):
                        end_time = sensor_data.index.max()
                        start_time = end_time - timedelta(days=7)
                        st.session_state.zoom_start_date = start_time
                        st.session_state.zoom_end_date = end_time
                        st.rerun()

                with col2:
                    if st.button("📅 Last 30 days"):
                        end_time = sensor_data.index.max()
                        start_time = end_time - timedelta(days=30)
                        st.session_state.zoom_start_date = start_time
                        st.session_state.zoom_end_date = end_time
                        st.rerun()

                with col3:
                    if st.button("📅 Last 90 days"):
                        end_time = sensor_data.index.max()
                        start_time = end_time - timedelta(days=90)
                        st.session_state.zoom_start_date = start_time
                        st.session_state.zoom_end_date = end_time
                        st.rerun()

                with col4:
                    if st.button("📅 Last 1 year"):
                        end_time = sensor_data.index.max()
                        start_time = end_time - timedelta(days=365)
                        st.session_state.zoom_start_date = start_time
                        st.session_state.zoom_end_date = end_time
                        st.rerun()

                with col5:
                    if st.button("📅 Last 2 years"):
                        end_time = sensor_data.index.max()
                        start_time = end_time - timedelta(days=731)
                        st.session_state.zoom_start_date = start_time
                        st.session_state.zoom_end_date = end_time
                        st.rerun()

                with col6:
                    if st.button("📅 Full range"):
                        st.session_state.zoom_start_date = None
                        st.session_state.zoom_end_date = None
                        st.rerun()

            else:
                st.warning("No data found for the selected sensors and time period.")

        with tab2:
            # Scatter plot
            scatter_fig, merged_data = create_comparison_plot(
                sensor_data, sensor1, sensor2, measurement_type, start_date, end_date
            )

            if scatter_fig is not None:
                st.plotly_chart(scatter_fig, use_container_width=True)

                # Display statistics in a compact format
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric(
                        f"Avg {measurement_type} (S1)", f"{merged_data[f'{measurement_type}_sensor1'].mean():.1f}"
                    )

                with col2:
                    st.metric(
                        f"Avg {measurement_type} (S2)", f"{merged_data[f'{measurement_type}_sensor2'].mean():.1f}"
                    )

                with col3:
                    correlation = merged_data[f"{measurement_type}_sensor1"].corr(
                        merged_data[f"{measurement_type}_sensor2"]
                    )
                    st.metric("Correlation", f"{correlation:.3f}")

                with col4:
                    st.metric("Data points", len(merged_data))
            else:
                st.warning("No overlapping data found for the selected sensors and time period.")
    else:
        st.warning("Please select two different sensors for comparison.")


if __name__ == "__main__":
    main()
