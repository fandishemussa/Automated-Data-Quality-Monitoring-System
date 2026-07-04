import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from data_sources.postgres_connector import create_postgres_engine


st.set_page_config(
    page_title="Data Quality Monitoring Dashboard",
    layout="wide"
)


def load_quality_runs():
    engine = create_postgres_engine()

    query = """
        SELECT *
        FROM data_quality_runs
        ORDER BY run_id DESC;
    """

    return pd.read_sql(query, engine)


def load_quality_results():
    engine = create_postgres_engine()

    query = """
        SELECT *
        FROM data_quality_results
        ORDER BY run_time DESC;
    """

    return pd.read_sql(query, engine)


st.title("Automated Data Quality Monitoring Dashboard")

runs_df = load_quality_runs()
results_df = load_quality_results()

if runs_df.empty:
    st.warning("No data quality runs found. Run `python main.py` first.")
else:
    latest_run = runs_df.iloc[0]
    latest_run_id = int(latest_run["run_id"])

    latest_results_df = results_df[results_df["run_id"] == latest_run_id]

    st.subheader("Latest Run Summary")

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    col1.metric("Run ID", latest_run_id)
    col2.metric("Quality Score", f"{latest_run['quality_score']}%")
    col3.metric("Total Checks", int(latest_run["total_checks"]))
    col4.metric("Passed", int(latest_run["passed_checks"]))
    col5.metric("Failed", int(latest_run["failed_checks"]))
    col6.metric("Critical", int(latest_run["critical_checks"]))

    st.write("**Latest run time:**", latest_run["run_time"])
    st.write("**Overall status:**", latest_run["overall_status"])

    st.divider()

    st.subheader("📈 Quality Score Trend")

    trend_df = runs_df.sort_values("run_id")[["run_id", "quality_score"]]
    trend_df = trend_df.set_index("run_id")

    st.line_chart(trend_df)

    st.divider()

    st.subheader("📌 Filters")

    selected_run_id = st.selectbox(
        "Select Run ID",
        options=runs_df["run_id"].tolist(),
        index=0
    )

    filtered_results = results_df[results_df["run_id"] == selected_run_id]

    datasets = ["All"] + sorted(filtered_results["dataset_name"].dropna().unique().tolist())

    selected_dataset = st.selectbox(
        "Select Dataset",
        options=datasets
    )

    if selected_dataset != "All":
        filtered_results = filtered_results[
            filtered_results["dataset_name"] == selected_dataset
        ]

    st.divider()

    st.subheader("🧪 Check Results")

    st.dataframe(filtered_results, width="stretch")

    st.subheader("❌ Failed Checks")

    failed_df = filtered_results[filtered_results["status"] == "FAIL"]

    if failed_df.empty:
        st.success("No failed checks for this selection.")
    else:
        st.dataframe(failed_df, width="stretch")

    st.subheader("🚨 Critical Issues")

    critical_df = filtered_results[filtered_results["severity"] == "CRITICAL"]

    if critical_df.empty:
        st.success("No critical issues for this selection.")
    else:
        st.dataframe(critical_df, width="stretch")

    st.divider()

    st.subheader("📊 Issues by Severity")

    if "severity" in filtered_results.columns and not filtered_results.empty:
        severity_df = filtered_results["severity"].value_counts().reset_index()
        severity_df.columns = ["severity", "count"]

        st.dataframe(severity_df, width="stretch")
        st.bar_chart(severity_df.set_index("severity"))
    else:
        st.info("No severity data available.")

    st.divider()

    st.subheader("📚 Run History")

    st.dataframe(runs_df, width="stretch")