"""
Chart and visualization components for the dashboard.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional


class ChartsDisplay:
    """Create and display various charts."""

    def __init__(self, processed_df: pd.DataFrame, aggregated_df: pd.DataFrame):
        """
        Initialize charts display.

        Args:
            processed_df: DataFrame with processed flight events
            aggregated_df: DataFrame with aggregated window data
        """
        self.processed_df = processed_df
        self.aggregated_df = aggregated_df

    def render_velocity_timeline(self):
        """Render velocity over time chart."""
        if self.processed_df.empty or "event_time" not in self.processed_df.columns or "velocity" not in self.processed_df.columns:
            st.info("No data available for velocity timeline")
            return

        try:
            # Sort by timestamp
            df_sorted = self.processed_df.sort_values("event_time").tail(100)

            fig = px.scatter(
                df_sorted,
                x="event_time",
                y="velocity",
                color="ml_is_anomaly" if "ml_is_anomaly" in df_sorted.columns else None,
                title="✈️ Flight Velocity Over Time",
                labels={"velocity": "Velocity (m/s)", "event_time": "Time"},
                hover_data=["icao24", "callsign", "velocity"]
            )
            fig.update_layout(hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Error rendering velocity chart: {e}")

    def render_altitude_timeline(self):
        """Render altitude over time chart."""
        if self.processed_df.empty or "event_time" not in self.processed_df.columns or "baro_altitude" not in self.processed_df.columns:
            st.info("No data available for altitude timeline")
            return

        try:
            df_sorted = self.processed_df.sort_values("event_time").tail(100)

            fig = px.scatter(
                df_sorted,
                x="event_time",
                y="baro_altitude",
                color="flight_phase" if "flight_phase" in df_sorted.columns else None,
                title="📈 Flight Altitude Over Time",
                labels={"baro_altitude": "Altitude (m)", "event_time": "Time"},
                hover_data=["icao24", "callsign", "baro_altitude"]
            )
            fig.update_layout(hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Error rendering altitude chart: {e}")

    def render_anomaly_scatter(self):
        """Render scatter plot highlighting anomalies."""
        if self.processed_df.empty or "velocity" not in self.processed_df.columns or "baro_altitude" not in self.processed_df.columns:
            st.info("No data available for anomaly scatter")
            return

        try:
            df_sample = self.processed_df.tail(200)

            fig = px.scatter(
                df_sample,
                x="velocity",
                y="baro_altitude",
                color="ml_is_anomaly" if "ml_is_anomaly" in df_sample.columns else None,
                size="ml_anomaly_score" if "ml_anomaly_score" in df_sample.columns else None,
                title="🚨 Anomaly Detection: Velocity vs Altitude",
                labels={"velocity": "Velocity (m/s)", "baro_altitude": "Altitude (m)"},
                hover_data=["icao24", "callsign"],
                color_discrete_map={True: "red", False: "blue"}
            )
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Error rendering anomaly scatter: {e}")

    def render_windowed_metrics(self):
        """Render windowed aggregation metrics."""
        if self.aggregated_df.empty:
            st.info("No aggregated data available yet")
            return

        try:
            # Velocity statistics per window
            if "avg_velocity" in self.aggregated_df.columns and "window_start" in self.aggregated_df.columns:
                st.subheader("📊 Windowed Velocity Statistics")
                df_vel = self.aggregated_df[["window_start", "avg_velocity", "max_velocity", "min_velocity"]].tail(20)
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=df_vel["window_start"],
                    y=df_vel["avg_velocity"],
                    name="Average",
                    mode="lines+markers"
                ))
                fig.add_trace(go.Scatter(
                    x=df_vel["window_start"],
                    y=df_vel["max_velocity"],
                    name="Max",
                    mode="lines",
                    line=dict(dash="dash")
                ))
                fig.add_trace(go.Scatter(
                    x=df_vel["window_start"],
                    y=df_vel["min_velocity"],
                    name="Min",
                    mode="lines",
                    line=dict(dash="dash")
                ))
                fig.update_layout(
                    title="Velocity Metrics Over Time Windows",
                    xaxis_title="Window Start",
                    yaxis_title="Velocity (m/s)",
                    hovermode="x unified"
                )
                st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Error rendering windowed metrics: {e}")

    def render_anomaly_count_trend(self):
        """Render trend of anomaly counts over time windows."""
        if self.aggregated_df.empty or "anomaly_count" not in self.aggregated_df.columns:
            st.info("No anomaly count data available")
            return

        try:
            df_anom = self.aggregated_df[["window_start", "anomaly_count"]].tail(30)

            fig = px.bar(
                df_anom,
                x="window_start",
                y="anomaly_count",
                title="🚨 Anomalies Per Time Window",
                labels={"window_start": "Window Start", "anomaly_count": "Anomaly Count"},
                color="anomaly_count",
                color_continuous_scale="Reds"
            )
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Error rendering anomaly trend: {e}")

    def render_aircraft_distribution(self):
        """Render distribution of events by aircraft."""
        if self.processed_df.empty or "icao24" not in self.processed_df.columns:
            st.info("No aircraft data available")
            return

        try:
            aircraft_counts = self.processed_df["icao24"].value_counts().head(15)
            
            aircraft_info = []
            for icao24 in aircraft_counts.index:
                callsign = self.processed_df[self.processed_df["icao24"] == icao24]["callsign"].iloc[0] if "callsign" in self.processed_df.columns else "N/A"
                count = aircraft_counts[icao24]
                aircraft_info.append({"Aircraft": callsign or icao24, "Events": count})
            
            df_aircraft = pd.DataFrame(aircraft_info)

            fig = px.bar(
                df_aircraft,
                x="Events",
                y="Aircraft",
                orientation="h",
                title="✈️ Top 15 Most Active Aircraft",
                labels={"Events": "Number of Events"}
            )
            fig.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Error rendering aircraft distribution: {e}")

    def render_flight_phase_distribution(self):
        """Render distribution of flight phases."""
        if self.processed_df.empty or "flight_phase" not in self.processed_df.columns:
            st.info("No flight phase data available")
            return

        try:
            phase_counts = self.processed_df["flight_phase"].value_counts()
            
            fig = px.pie(
                values=phase_counts.values,
                names=phase_counts.index,
                title="🛫 Flight Phase Distribution",
                labels={"names": "Phase", "values": "Count"}
            )
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Error rendering flight phase distribution: {e}")

    def render_altitude_vs_vertical_rate(self):
        """Render altitude vs vertical rate for climb/descent analysis."""
        if self.processed_df.empty or "baro_altitude" not in self.processed_df.columns or "vertical_rate" not in self.processed_df.columns:
            st.info("No altitude/vertical rate data available")
            return

        try:
            df_sample = self.processed_df.tail(300)
            
            fig = px.scatter(
                df_sample,
                x="vertical_rate",
                y="baro_altitude",
                color="flight_phase" if "flight_phase" in df_sample.columns else None,
                title="📊 Climb/Descent Analysis: Altitude vs Vertical Rate",
                labels={"vertical_rate": "Vertical Rate (m/s)", "baro_altitude": "Altitude (m)"},
                hover_data=["icao24", "callsign"],
                size_max=8
            )
            fig.add_vline(x=0, line_dash="dash", line_color="gray", annotation_text="No Vertical Movement")
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Error rendering altitude vs vertical rate: {e}")

    def render_country_distribution(self):
        """Render distribution of flights by origin country."""
        if self.processed_df.empty or "origin_country" not in self.processed_df.columns:
            st.info("No country data available")
            return

        try:
            country_counts = self.processed_df["origin_country"].value_counts().head(12)
            
            fig = px.bar(
                x=country_counts.values,
                y=country_counts.index,
                orientation="h",
                title="🌍 Top 12 Countries by Flight Count",
                labels={"x": "Number of Flights", "y": "Country"},
                color=country_counts.values,
                color_continuous_scale="Blues"
            )
            fig.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Error rendering country distribution: {e}")

    def render_velocity_distribution(self):
        """Render distribution of flight velocities (histogram)."""
        if self.processed_df.empty or "velocity" not in self.processed_df.columns:
            st.info("No velocity data available")
            return

        try:
            fig = px.histogram(
                self.processed_df,
                x="velocity",
                nbins=40,
                title="📉 Velocity Distribution",
                labels={"velocity": "Velocity (m/s)", "count": "Number of Events"},
                color_discrete_sequence=["steelblue"]
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Error rendering velocity distribution: {e}")

    def render_heading_distribution(self):
        """Render distribution of flight headings (direction)."""
        if self.processed_df.empty or "heading" not in self.processed_df.columns:
            st.info("No heading data available")
            return

        try:
            # Create compass rose plot
            headings = self.processed_df["heading"].dropna()
            if len(headings) == 0:
                st.info("No heading data available")
                return

            # Bin headings into compass directions
            bins = [0, 45, 90, 135, 180, 225, 270, 315, 360]
            labels = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
            heading_dirs = pd.cut(headings, bins=bins, labels=labels, right=False)
            dir_counts = heading_dirs.value_counts()

            fig = px.bar(
                x=dir_counts.index,
                y=dir_counts.values,
                title="🧭 Flight Direction Distribution",
                labels={"x": "Direction", "y": "Number of Flights"},
                color=dir_counts.values,
                color_continuous_scale="Viridis"
            )
            fig.update_layout(showlegend=False, xaxis={'categoryorder': 'array', 'categoryarray': labels})
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Error rendering heading distribution: {e}")

    def render_on_ground_status(self):
        """Render on-ground vs in-air status."""
        if self.processed_df.empty or "on_ground" not in self.processed_df.columns:
            st.info("No on-ground status data available")
            return

        try:
            status_counts = self.processed_df["on_ground"].value_counts()
            status_labels = {True: "On Ground", False: "In Air"}
            
            status_data = [
                {"Status": status_labels.get(idx, str(idx)), "Count": count}
                for idx, count in status_counts.items()
            ]
            df_status = pd.DataFrame(status_data)

            fig = px.pie(
                df_status,
                values="Count",
                names="Status",
                title="✈️ Aircraft Status Distribution",
                color_discrete_map={"On Ground": "orange", "In Air": "blue"}
            )
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Error rendering on-ground status: {e}")

    def render_data_quality_metrics(self):
        """Render data quality and processing metrics."""
        try:
            metrics_data = {
                "Metric": [
                    "Total Events Processed",
                    "Unique Aircraft",
                    "Events with Valid Position",
                    "Events with Altitude",
                    "Average Events/Aircraft"
                ],
                "Value": [
                    len(self.processed_df),
                    self.processed_df["icao24"].nunique() if "icao24" in self.processed_df.columns else 0,
                    len(self.processed_df[self.processed_df["latitude"].notna()]) if "latitude" in self.processed_df.columns else 0,
                    len(self.processed_df[self.processed_df["baro_altitude"].notna()]) if "baro_altitude" in self.processed_df.columns else 0,
                    round(len(self.processed_df) / max(self.processed_df["icao24"].nunique(), 1), 1) if "icao24" in self.processed_df.columns else 0
                ]
            }
            df_metrics = pd.DataFrame(metrics_data)

            fig = px.bar(
                df_metrics,
                x="Metric",
                y="Value",
                title="📊 Data Quality Metrics",
                color="Value",
                color_continuous_scale="Greens",
                text="Value"
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Error rendering data quality metrics: {e}")
