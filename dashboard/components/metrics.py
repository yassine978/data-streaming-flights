"""
Metrics display components for the dashboard.
Shows KPIs and summary statistics.
"""

import streamlit as st
import pandas as pd
from typing import Optional


class MetricsDisplay:
    """Display key performance indicators and metrics."""

    def __init__(self, processed_df: pd.DataFrame, aggregated_df: pd.DataFrame):
        """
        Initialize metrics display.

        Args:
            processed_df: DataFrame with processed flight events
            aggregated_df: DataFrame with aggregated window data
        """
        self.processed_df = processed_df
        self.aggregated_df = aggregated_df

    def render_top_metrics(self):
        """Render top-level KPI metrics."""
        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            total_events = len(self.processed_df)
            st.metric(
                label="📊 Total Events",
                value=f"{total_events:,}",
                delta=None
            )

        with col2:
            if not self.processed_df.empty and "ml_is_anomaly" in self.processed_df.columns:
                anomalies = self.processed_df["ml_is_anomaly"].sum()
                anomaly_rate = (anomalies / len(self.processed_df) * 100) if len(self.processed_df) > 0 else 0
                st.metric(
                    label="🚨 Anomalies",
                    value=f"{anomalies}",
                    delta=f"{anomaly_rate:.1f}%"
                )
            else:
                st.metric("🚨 Anomalies", "N/A")

        with col3:
            if not self.processed_df.empty and "velocity" in self.processed_df.columns:
                avg_velocity = self.processed_df["velocity"].mean()
                st.metric(
                    label="✈️ Avg Velocity",
                    value=f"{avg_velocity:.1f} m/s",
                    delta=None
                )
            else:
                st.metric("✈️ Avg Velocity", "N/A")

        with col4:
            if not self.processed_df.empty and "baro_altitude" in self.processed_df.columns:
                avg_altitude = self.processed_df["baro_altitude"].mean()
                st.metric(
                    label="📈 Avg Altitude",
                    value=f"{avg_altitude:,.0f} m",
                    delta=None
                )
            else:
                st.metric("📈 Avg Altitude", "N/A")

        with col5:
            unique_aircraft = len(self.processed_df["icao24"].unique()) if not self.processed_df.empty and "icao24" in self.processed_df.columns else 0
            st.metric(
                label="🛫 Aircraft",
                value=f"{unique_aircraft}",
                delta=None
            )

    def render_summary_stats(self):
        """Render summary statistics for processed data."""
        if self.processed_df.empty:
            st.info("No processed data available yet.")
            return

        st.subheader("📊 Summary Statistics")

        cols = st.columns(3)

        with cols[0]:
            st.write("**Velocity (m/s)**")
            if "velocity" in self.processed_df.columns:
                st.text(
                    f"Min:  {self.processed_df['velocity'].min():.2f}\n"
                    f"Mean: {self.processed_df['velocity'].mean():.2f}\n"
                    f"Max:  {self.processed_df['velocity'].max():.2f}"
                )

        with cols[1]:
            st.write("**Altitude (m)**")
            if "baro_altitude" in self.processed_df.columns:
                st.text(
                    f"Min:  {self.processed_df['baro_altitude'].min():.0f}\n"
                    f"Mean: {self.processed_df['baro_altitude'].mean():.0f}\n"
                    f"Max:  {self.processed_df['baro_altitude'].max():.0f}"
                )

        with cols[2]:
            st.write("**Vertical Rate (m/s)**")
            if "vertical_rate" in self.processed_df.columns:
                st.text(
                    f"Min:  {self.processed_df['vertical_rate'].min():.2f}\n"
                    f"Mean: {self.processed_df['vertical_rate'].mean():.2f}\n"
                    f"Max:  {self.processed_df['vertical_rate'].max():.2f}"
                )

    def render_anomaly_stats(self):
        """Render anomaly-specific statistics."""
        if self.processed_df.empty or "ml_is_anomaly" not in self.processed_df.columns:
            st.info("No anomaly data available.")
            return

        st.subheader("🚨 Anomaly Analysis")

        cols = st.columns(3)

        with cols[0]:
            anomaly_count = self.processed_df["ml_is_anomaly"].sum()
            st.metric("Anomalies Detected", f"{int(anomaly_count)}")

        with cols[1]:
            anomaly_pct = (self.processed_df["ml_is_anomaly"].sum() / len(self.processed_df) * 100)
            st.metric("Anomaly Rate", f"{anomaly_pct:.2f}%")

        with cols[2]:
            if "ml_anomaly_score" in self.processed_df.columns:
                avg_score = self.processed_df["ml_anomaly_score"].mean()
                st.metric("Avg Anomaly Score", f"{avg_score:.4f}")

        # Top anomalous flights
        if "ml_is_anomaly" in self.processed_df.columns:
            anomalous = self.processed_df[self.processed_df["ml_is_anomaly"] == True]
            if not anomalous.empty:
                st.write("**Recent Anomalies:**")
                display_cols = ["icao24", "callsign", "velocity", "ml_anomaly_score"]
                display_cols = [c for c in display_cols if c in anomalous.columns]
                st.dataframe(
                    anomalous[display_cols].tail(10),
                    use_container_width=True,
                    hide_index=True
                )
