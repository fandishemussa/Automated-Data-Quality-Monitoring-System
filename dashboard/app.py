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
        ORDER BY id DESC;
    """

    return pd.read_sql(query, engine)


def load_issue_details():
    engine = create_postgres_engine()

    query = """
        SELECT *
        FROM data_quality_issue_details
        ORDER BY id DESC;
    """

    return pd.read_sql(query, engine)
def load_alerts():
    engine = create_postgres_engine()

    query = """
        SELECT *
        FROM data_quality_alerts
        ORDER BY id DESC;
    """

    return pd.read_sql(query, engine)

st.title("Automated Data Quality Monitoring Dashboard")

runs_df = load_quality_runs()
results_df = load_quality_results()
details_df = load_issue_details()
alerts_df = load_alerts()

if runs_df.empty:
    st.warning("No data quality runs found. Run `python main.py` first.")
else:
    latest_run = runs_df.iloc[0]
    latest_run_id = int(latest_run["run_id"])

    latest_results_df = results_df[results_df["run_id"] == latest_run_id]
    latest_alerts_df = alerts_df[alerts_df["run_id"] == latest_run_id]
    unresolved_alerts_count = len(latest_alerts_df[latest_alerts_df["is_resolved"] == False])

    st.subheader("Latest Run Summary")

    col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
    col7.metric("Alerts", unresolved_alerts_count)
    col1.metric("Run ID", latest_run_id)
    col2.metric("Quality Score", f"{latest_run['quality_score']}%")
    col3.metric("Total Checks", int(latest_run["total_checks"]))
    col4.metric("Passed", int(latest_run["passed_checks"]))
    col5.metric("Failed", int(latest_run["failed_checks"]))
    col6.metric("Critical", int(latest_run["critical_checks"]))

    st.write("**Latest run time:**", latest_run["run_time"])
    st.write("**Overall status:**", latest_run["overall_status"])
    st.divider()

    st.subheader("Latest Run Alerts")

    if latest_alerts_df.empty:
        st.success("No alerts for the latest run.")
    else:
        unresolved_latest_alerts = latest_alerts_df[
            latest_alerts_df["is_resolved"] == False
            ]

        if unresolved_latest_alerts.empty:
            st.success("All alerts for the latest run are resolved.")
        else:
            st.dataframe(unresolved_latest_alerts, width="stretch")
    st.divider()

    st.subheader("Quality Score Trend")

    trend_df = runs_df.sort_values("run_id")[["run_id", "quality_score"]]
    trend_df = trend_df.set_index("run_id")

    st.line_chart(trend_df)

    st.divider()

    st.subheader("Filters")

    selected_run_id = st.selectbox(
        "Select Run ID",
        options=runs_df["run_id"].tolist(),
        index=0
    )

    filtered_results = results_df[results_df["run_id"] == selected_run_id]
    filtered_details = details_df[details_df["run_id"] == selected_run_id]
    filtered_alerts = alerts_df[alerts_df["run_id"] == selected_run_id]
    datasets = ["All"] + sorted(
        filtered_results["dataset_name"].dropna().unique().tolist()
    )

    selected_dataset = st.selectbox(
        "Select Dataset",
        options=datasets
    )

    if selected_dataset != "All":
        filtered_results = filtered_results[
            filtered_results["dataset_name"] == selected_dataset
        ]

        filtered_details = filtered_details[
            filtered_details["dataset_name"] == selected_dataset
        ]

    st.divider()

    st.subheader(" Check Results")

    if filtered_results.empty:
        st.info("No check results found for this selection.")
    else:
        st.dataframe(filtered_results, width="stretch")

    st.subheader("Failed Checks")

    failed_df = filtered_results[filtered_results["status"] == "FAIL"]

    if failed_df.empty:
        st.success("No failed checks for this selection.")
    else:
        st.dataframe(failed_df, width="stretch")

    st.subheader("Critical Issues")

    critical_df = filtered_results[filtered_results["severity"] == "CRITICAL"]

    if critical_df.empty:
        st.success("No critical issues for this selection.")
    else:
        st.dataframe(critical_df, width="stretch")

    st.subheader("Alerts for Selected Run")

    if filtered_alerts.empty:
        st.success("No alerts for this run.")
    else:
        st.dataframe(filtered_alerts, width="stretch")

    st.divider()

    st.subheader("Issue Details / Bad Row Examples")

    if filtered_details.empty:
        st.success("No bad-row examples found for this selection.")
    else:
        detail_columns = [
            "dataset_name",
            "check_type",
            "column_name",
            "row_identifier",
            "bad_value",
            "reason",
            "sample_row",
            "created_at"
        ]

        available_detail_columns = [
            col for col in detail_columns
            if col in filtered_details.columns
        ]

        st.dataframe(
            filtered_details[available_detail_columns],
            width="stretch"
        )

        with st.expander("View raw issue details"):
            st.dataframe(filtered_details, width="stretch")

    st.divider()

    st.subheader("Issues by Severity")

    if "severity" in filtered_results.columns and not filtered_results.empty:
        severity_df = filtered_results["severity"].value_counts().reset_index()
        severity_df.columns = ["severity", "count"]

        st.dataframe(severity_df, width="stretch")
        st.bar_chart(severity_df.set_index("severity"))
    else:
        st.info("No severity data available.")

    st.divider()

    st.subheader("Run History")

    st.dataframe(runs_df, width="stretch")