import asyncio
import os
import sys
from pathlib import Path

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

API_BASE = os.environ.get(
    "API_URL",
    f"https://{os.environ.get('RAILWAY_SERVICE_SH_PDOPS_URL', 'localhost:8000')}"
) + "/api/v1"

st.set_page_config(
    page_title="SH-PDOPS Dashboard",
    page_icon="🔄",
    layout="wide",
)

st.title("SH-PDOPS: Self-Healing + Predictive DevOps System")
st.markdown("Real-time monitoring, anomaly detection, prediction, and self-healing.")


@st.cache_data(ttl=2)
def fetch_json(endpoint: str) -> dict | list:
    try:
        resp = httpx.get(f"{API_BASE}{endpoint}", timeout=5)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return []


@st.cache_data(ttl=2)
def fetch_health() -> dict:
    try:
        resp = httpx.get(f"{API_BASE}/health", timeout=5)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return {}


@st.cache_data(ttl=5)
def fetch_stats() -> dict:
    try:
        resp = httpx.get(f"{API_BASE}/stats", timeout=5)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return {}


col1, col2, col3, col4, col5 = st.columns(5)
health = fetch_health()

with col1:
    status_color = "🟢" if health.get("status") == "healthy" else "🔴"
    st.metric("System Status", f"{status_color} {health.get('status', 'N/A').upper()}")

with col2:
    health_score = health.get("health_score", 0)
    st.metric("Health Score", f"{health_score:.1f}%")

with col3:
    st.metric("Metrics", health.get("metrics_collected", 0))

with col4:
    st.metric("Active Anomalies", health.get("anomalies_active", 0))

with col5:
    st.metric("Actions Taken", health.get("actions_total", 0))

stats = fetch_stats()
col6, col7, col8, col9 = st.columns(4)

with col6:
    st.metric("Success Rate", f"{stats.get('success_rate', 0):.1f}%")

with col7:
    st.metric("Avg Failure Prob", f"{stats.get('avg_failure_probability', 0):.1f}%")

with col8:
    st.metric("Anomaly Rate", f"{stats.get('anomaly_rate', 0):.1f}%")

with col9:
    st.metric("Predictions", stats.get("total_predictions", 0))

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["📊 Metrics", "⚠️ Anomalies", "🔮 Predictions", "🛠️ Actions", "⚙️ Controls"]
)

with tab1:
    st.subheader("Live Metrics")
    metrics_data = fetch_json("/metrics?minutes=2")
    if metrics_data:
        df = pd.DataFrame(metrics_data)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        services = df["name"].unique()
        selected_metric = st.selectbox("Select Metric", services)
        metric_df = df[df["name"] == selected_metric]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=metric_df["timestamp"],
            y=metric_df["value"],
            mode="lines+markers",
            name=selected_metric,
        ))
        fig.update_layout(
            title=f"{selected_metric} - Real-time",
            xaxis_title="Time",
            yaxis_title="Value",
            height=400,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No metrics data available. Ensure the API is running.")

with tab2:
    st.subheader("Anomaly Events")
    anomalies = fetch_json("/anomalies")
    if anomalies:
        df = pd.DataFrame(anomalies)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        severity_colors = {
            "info": "blue", "warning": "orange",
            "critical": "red", "fatal": "darkred",
        }
        fig = px.scatter(
            df,
            x="timestamp",
            y="metric_name",
            color="severity",
            size="score",
            hover_data=["description", "anomaly_type"],
            title="Anomaly Timeline",
            color_discrete_map=severity_colors,
            height=400,
        )
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(
            df[["id", "timestamp", "metric_name", "severity", "score", "description"]],
            use_container_width=True,
        )
    else:
        st.info("No anomalies detected.")

with tab3:
    st.subheader("Failure Predictions")
    preds = fetch_json("/predictions?high_risk_only=true")
    if preds:
        df = pd.DataFrame(preds)
        df["timestamp"] = pd.to_datetime(df["timestamp"])

        col_a, col_b = st.columns(2)
        with col_a:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df["metric_name"],
                y=df["failure_probability"],
                name="Failure Probability",
                marker_color=df["failure_probability"].apply(
                    lambda x: "red" if x > 0.7 else "orange" if x > 0.4 else "green"
                ),
            ))
            fig.update_layout(
                title="Failure Probability by Metric",
                xaxis_title="Metric",
                yaxis_title="Probability",
                height=400,
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_b:
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=df["metric_name"],
                y=df["time_to_failure_minutes"],
                mode="markers+text",
                marker=dict(
                    size=df["confidence"] * 30,
                    color=df["failure_probability"],
                    colorscale="RdYlGn_r",
                    showscale=True,
                ),
                text=df["time_to_failure_minutes"].round(1),
                textposition="top center",
            ))
            fig2.update_layout(
                title="Time to Failure (minutes)",
                xaxis_title="Metric",
                yaxis_title="Minutes",
                height=400,
            )
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No high-risk predictions.")

with tab4:
    st.subheader("Remediation Actions")
    actions = fetch_json("/actions")
    if actions:
        df = pd.DataFrame(actions)
        if "triggered_at" in df.columns:
            df["triggered_at"] = pd.to_datetime(df["triggered_at"])

        status_counts = df["status"].value_counts()
        fig = px.pie(
            values=status_counts.values,
            names=status_counts.index,
            title="Action Status Distribution",
            color_discrete_sequence=px.colors.qualitative.Set3,
            height=350,
        )
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(
            df[["id", "action_type", "target", "status", "risk", "triggered_at"]],
            use_container_width=True,
        )
    else:
        st.info("No actions recorded.")

with tab5:
    st.subheader("Fault Injection & Controls")
    st.markdown("Inject simulated faults to test the self-healing system.")

    fault_types = {
        "CPU Spike": "cpu_spike",
        "Memory Leak": "memory_leak",
        "Latency Burst": "latency_burst",
        "Error Burst": "error_burst",
        "Traffic Surge": "traffic_surge",
    }

    col_a, col_b = st.columns(2)
    with col_a:
        selected_fault = st.selectbox("Fault Type", list(fault_types.keys()))
        duration = st.slider("Duration (seconds)", 10, 60, 30)

        if st.button("🚨 Inject Fault", type="primary"):
            try:
                resp = httpx.post(
                    f"{API_BASE}/simulate/fault",
                    json={
                        "fault_type": fault_types[selected_fault],
                        "duration_seconds": duration,
                    },
                    timeout=5,
                )
                st.success(f"Fault injected: {selected_fault}")
            except Exception as e:
                st.error(f"Failed: {e}")

        if st.button("🛑 Stop Fault"):
            try:
                httpx.post(f"{API_BASE}/simulate/stop-fault", timeout=5)
                st.success("Fault stopped")
            except Exception as e:
                st.error(f"Failed: {e}")

    with col_b:
        st.markdown("### Healer Mode")
        mode_map = {"Auto": "auto", "Semi-Auto": "semi_auto", "Manual": "manual"}
        # Read-only display for now
        st.info(f"Current mode: {health.get('healer_mode', 'unknown')}")

        pending = fetch_json("/actions?pending_only=true")
        if pending:
            st.warning(f"⚠️ {len(pending)} action(s) pending approval")
            for act in pending:
                st.markdown(
                    f"- **{act['action_type']}** on `{act['target']}` "
                    f"(risk: {act['risk']})"
                )
        else:
            st.success("No pending actions")
