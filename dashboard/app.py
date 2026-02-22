"""
Real-time Flight Data Streaming Dashboard
A Streamlit application for visualizing flight tracking data from Apache Kafka.

Run with:
    streamlit run dashboard/app.py
"""

import streamlit as st
import pandas as pd
import logging
import time
from datetime import datetime
from components.kafka_consumer import DashboardKafkaConsumer
from components.metrics import MetricsDisplay
from components.charts import ChartsDisplay

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Flight Data Streaming Dashboard",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3em;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1em;
    }
    .status-online {
        background-color: #90EE90;
        color: black;
        padding: 10px;
        border-radius: 5px;
        display: inline-block;
    }
    .status-offline {
        background-color: #FFB6C6;
        color: black;
        padding: 10px;
        border-radius: 5px;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# Sidebar Configuration
# ═══════════════════════════════════════════════════════════════════════════

st.sidebar.header("⚙️ Configuration")

# Data fetching settings
refresh_interval = st.sidebar.slider(
    "Refresh Interval (seconds)",
    min_value=1,
    max_value=10,
    value=3,
    help="How often to fetch new data from Kafka"
)

auto_refresh = st.sidebar.checkbox(
    "🔄 Auto-Refresh",
    value=True,
    help="Enable automatic dashboard refresh"
)

processed_limit = st.sidebar.slider(
    "Processed Events Buffer",
    min_value=50,
    max_value=500,
    value=200,
    help="Maximum number of processed events to display"
)

aggregated_limit = st.sidebar.slider(
    "Aggregated Windows Buffer",
    min_value=20,
    max_value=100,
    value=50,
    help="Maximum number of aggregated windows to display"
)

# Kafka connection settings
st.sidebar.subheader("🔗 Kafka Connection")
kafka_servers = st.sidebar.text_input(
    "Kafka Bootstrap Servers",
    value="localhost:9092",
    help="Comma-separated list of Kafka bootstrap servers"
)

# Display settings
st.sidebar.subheader("📊 Display Options")
show_processed = st.sidebar.checkbox("Show Processed Events", value=True)
show_aggregated = st.sidebar.checkbox("Show Aggregated Data", value=True)
show_raw_tables = st.sidebar.checkbox("Show Raw Data Tables", value=False)

# ═══════════════════════════════════════════════════════════════════════════
# Initialize Kafka Consumer
# ═══════════════════════════════════════════════════════════════════════════

@st.cache_resource
def get_kafka_consumer():
    """Initialize Kafka consumer (cached)."""
    return DashboardKafkaConsumer(bootstrap_servers=kafka_servers)


try:
    kafka_consumer = get_kafka_consumer()
    kafka_ready = True
except Exception as e:
    logger.error(f"Failed to initialize Kafka consumer: {e}")
    kafka_ready = False

# ═══════════════════════════════════════════════════════════════════════════
# Main Dashboard
# ═══════════════════════════════════════════════════════════════════════════

# Header
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown("# ✈️ Real-Time Flight Tracking Dashboard")
    st.markdown("---")

with col2:
    if kafka_ready:
        st.markdown('<div class="status-online">● Online</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-offline">● Offline</div>', unsafe_allow_html=True)

# Data containers
if "processed_data" not in st.session_state:
    st.session_state.processed_data = []
if "aggregated_data" not in st.session_state:
    st.session_state.aggregated_data = []

# Main refresh loop
placeholder = st.empty()
last_update = st.empty()

def update_data():
    """Fetch latest data from Kafka."""
    if not kafka_ready:
        return

    try:
        processed, aggregated = kafka_consumer.fetch_both(
            processed_limit=processed_limit,
            aggregated_limit=aggregated_limit
        )

        st.session_state.processed_data = processed
        st.session_state.aggregated_data = aggregated

        return True
    except Exception as e:
        logger.error(f"Error fetching data: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════════
# Dashboard Content
# ═══════════════════════════════════════════════════════════════════════════

# Fetch data from Kafka
if kafka_ready:
    update_data()

# Convert to DataFrames
df_processed = pd.DataFrame(st.session_state.processed_data) if st.session_state.processed_data else pd.DataFrame()
df_aggregated = pd.DataFrame(st.session_state.aggregated_data) if st.session_state.aggregated_data else pd.DataFrame()

# Display last update time
with last_update.container():
    col1, col2 = st.columns([3, 1])
    with col2:
        st.caption(f"🕐 Last updated: {datetime.now().strftime('%H:%M:%S')}")

# ═══════════════════════════════════════════════════════════════════════════
# Metrics Section
# ═══════════════════════════════════════════════════════════════════════════

if not df_processed.empty:
    metrics_display = MetricsDisplay(df_processed, df_aggregated)
    metrics_display.render_top_metrics()
    st.divider()

    # Summary stats
    col1, col2 = st.columns(2)
    with col1:
        metrics_display.render_summary_stats()
    with col2:
        metrics_display.render_anomaly_stats()

# ═══════════════════════════════════════════════════════════════════════════
# Charts Section
# ═══════════════════════════════════════════════════════════════════════════

if show_processed and not df_processed.empty:
    st.divider()
    st.subheader("📊 Real-Time Event Analysis")

    charts = ChartsDisplay(df_processed, df_aggregated)

    col1, col2 = st.columns(2)
    with col1:
        charts.render_velocity_timeline()
    with col2:
        charts.render_altitude_timeline()

    col3, col4 = st.columns(2)
    with col3:
        charts.render_anomaly_scatter()
    with col4:
        charts.render_aircraft_distribution()

    col5, col6 = st.columns(2)
    with col5:
        charts.render_flight_phase_distribution()
    with col6:
        charts.render_altitude_vs_vertical_rate()

# ═══════════════════════════════════════════════════════════════════════════
# Advanced Analytics Section
# ═══════════════════════════════════════════════════════════════════════════

if show_processed and not df_processed.empty:
    st.divider()
    st.subheader("🔍 Advanced Analytics")

    col7, col8 = st.columns(2)
    with col7:
        charts.render_country_distribution()
    with col8:
        charts.render_velocity_distribution()

    col9, col10 = st.columns(2)
    with col9:
        charts.render_heading_distribution()
    with col10:
        charts.render_on_ground_status()

    col11 = st.columns(1)[0]
    with col11:
        charts.render_data_quality_metrics()

if show_aggregated and not df_aggregated.empty:
    st.divider()
    st.subheader("📈 Windowed Aggregations")

    charts = ChartsDisplay(df_processed, df_aggregated)

    col1, col2 = st.columns(2)
    with col1:
        charts.render_windowed_metrics()
    with col2:
        charts.render_anomaly_count_trend()

# ═══════════════════════════════════════════════════════════════════════════
# Data Tables
# ═══════════════════════════════════════════════════════════════════════════

if show_raw_tables:
    st.divider()
    st.subheader("📋 Raw Data")

    tab1, tab2 = st.tabs(["Processed Events", "Aggregated Windows"])

    with tab1:
        if not df_processed.empty:
            st.dataframe(
                df_processed.tail(50),
                width='stretch',
                height=400
            )
        else:
            st.info("No processed data available")

    with tab2:
        if not df_aggregated.empty:
            st.dataframe(
                df_aggregated.tail(30),
                width='stretch',
                height=400
            )
        else:
            st.info("No aggregated data available")

# ═══════════════════════════════════════════════════════════════════════════
# Auto-Refresh Loop
# ═══════════════════════════════════════════════════════════════════════════

if auto_refresh and kafka_ready:
    time.sleep(refresh_interval)
    st.rerun()
