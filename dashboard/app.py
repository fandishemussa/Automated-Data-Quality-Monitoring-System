import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_sources.postgres_connector import create_postgres_engine


st.set_page_config(
    page_title="Data Quality Monitoring Dashboard",
    layout="wide",
)

STATISTICAL_CHECK_TYPES = [
    "z_score_anomaly_check",
    "data_drift_check",
    "statistical_check_error",
]


def load_query(query, table_name):
    """Load dashboard data and return an empty DataFrame on table errors."""

    engine = create_postgres_engine()

    try:
        return pd.read_sql(text(query), engine)
    except SQLAlchemyError as exc:
        st.warning(
            f"Could not load `{table_name}`. Run `python database/init_db.py` "
            "if the monitoring tables have not been created yet."
        )
        st.caption(str(exc))
        return pd.DataFrame()


def load_quality_runs():
    return load_query(
        """
        SELECT *
        FROM data_quality_runs
        ORDER BY run_id DESC;
        """,
        "data_quality_runs",
    )


def load_quality_results():
    return load_query(
        """
        SELECT *
        FROM data_quality_results
        ORDER BY id DESC;
        """,
        "data_quality_results",
    )


def load_issue_details():
    return load_query(
        """
        SELECT *
        FROM data_quality_issue_details
        ORDER BY id DESC;
        """,
        "data_quality_issue_details",
    )


def load_alerts():
    return load_query(
        """
        SELECT *
        FROM data_quality_alerts
        ORDER BY id DESC;
        """,
        "data_quality_alerts",
    )
def update_alert(alert_id, alert_type, severity, message, is_resolved):
    """Update alert information from the dashboard."""

    engine = create_postgres_engine()

    query = text("""
        UPDATE data_quality_alerts
        SET
            alert_type = :alert_type,
            severity = :severity,
            message = :message,
            is_resolved = :is_resolved
        WHERE id = :alert_id;
    """)

    try:
        with engine.begin() as connection:
            connection.execute(
                query,
                {
                    "alert_id": int(alert_id),
                    "alert_type": alert_type,
                    "severity": severity,
                    "message": message,
                    "is_resolved": bool(is_resolved),
                },
            )

        return True

    except SQLAlchemyError as exc:
        st.error("Could not update alert.")
        st.caption(str(exc))
        return False


def resolve_alert(alert_id):
    """Mark an alert as resolved."""

    engine = create_postgres_engine()

    query = text("""
        UPDATE data_quality_alerts
        SET is_resolved = TRUE
        WHERE id = :alert_id;
    """)

    try:
        with engine.begin() as connection:
            connection.execute(query, {"alert_id": int(alert_id)})

        return True

    except SQLAlchemyError as exc:
        st.error("Could not resolve alert.")
        st.caption(str(exc))
        return False

def load_profile_results():
    return load_query(
        """
        SELECT *
        FROM data_profile_results
        ORDER BY id DESC;
        """,
        "data_profile_results",
    )


def unique_options(df, column):
    """Return sorted non-null values for a filter."""

    if df.empty or column not in df.columns:
        return []

    return sorted(df[column].dropna().unique().tolist())


def filter_by_value(df, column, value):
    """Filter a DataFrame if the selected value is not All."""

    if df.empty or column not in df.columns or value == "All":
        return df.copy()

    return df[df[column] == value]


def rows_matching(df, column, value):
    """Return rows matching a value or an empty frame when the column is absent."""

    if df.empty or column not in df.columns:
        return df.iloc[0:0].copy()

    return df[df[column] == value]


def filter_details_by_results(details_df, results_df):
    """Keep issue details aligned with status/severity-filtered results."""

    if details_df.empty or results_df.empty:
        return details_df.iloc[0:0].copy()

    if "result_id" in details_df.columns and "id" in results_df.columns:
        return details_df[details_df["result_id"].isin(results_df["id"])]

    if "check_type" in details_df.columns and "check_type" in results_df.columns:
        return details_df[details_df["check_type"].isin(results_df["check_type"])]

    return details_df


def alert_resolved_mask(alerts_df):
    """Return a boolean mask for resolved alerts across bool/string DB values."""

    if alerts_df.empty or "is_resolved" not in alerts_df.columns:
        return pd.Series(False, index=alerts_df.index)

    resolved_values = alerts_df["is_resolved"].fillna(False)

    if resolved_values.dtype == object:
        return resolved_values.astype(str).str.lower().isin(["true", "1", "yes"])

    return resolved_values.astype(bool)


def filter_unresolved_alerts(alerts_df):
    """Return unresolved alerts while tolerating boolean/string DB values."""

    if alerts_df.empty:
        return alerts_df

    return alerts_df[~alert_resolved_mask(alerts_df)]


def filter_resolved_alerts(alerts_df):
    """Return resolved alerts while tolerating boolean/string DB values."""

    if alerts_df.empty:
        return alerts_df

    return alerts_df[alert_resolved_mask(alerts_df)]


def unresolved_alert_count(alerts_df):
    """Count unresolved alerts while tolerating boolean/string DB values."""

    if alerts_df.empty:
        return 0

    return len(filter_unresolved_alerts(alerts_df))


def build_quality_trend_frame(runs_df, alerts_df):
    """Prepare run history for the quality trend chart."""

    if runs_df.empty:
        return pd.DataFrame()

    trend = runs_df.sort_values("run_id").copy()
    trend["quality_score"] = pd.to_numeric(
        trend["quality_score"],
        errors="coerce",
    )
    trend["rolling_average"] = (
        trend["quality_score"]
        .rolling(window=3, min_periods=1)
        .mean()
        .round(2)
    )
    trend["run_label"] = trend["run_id"].astype(str)
    if "overall_status" in trend.columns:
        trend["status"] = trend["overall_status"].fillna("UNKNOWN")
    else:
        trend["status"] = "UNKNOWN"

    if not alerts_df.empty and "run_id" in alerts_df.columns:
        alert_counts = (
            alerts_df
            .groupby("run_id")
            .size()
            .rename("alerts")
            .reset_index()
        )
        trend = trend.merge(alert_counts, on="run_id", how="left")
    else:
        trend["alerts"] = 0

    trend["alerts"] = trend["alerts"].fillna(0).astype(int)
    trend["score_band"] = pd.cut(
        trend["quality_score"],
        bins=[-0.01, 79.99, 89.99, 100],
        labels=["Needs attention", "Watch", "Healthy"],
    )

    return trend


def render_metrics(latest_run, latest_alerts_df):
    """Render latest-run KPI cards."""

    metric_cols = st.columns(7)
    metric_cols[0].metric("Latest Run ID", int(latest_run["run_id"]))
    metric_cols[1].metric("Quality Score", f"{latest_run['quality_score']}%")
    metric_cols[2].metric("Total Checks", int(latest_run["total_checks"]))
    metric_cols[3].metric("Passed Checks", int(latest_run["passed_checks"]))
    metric_cols[4].metric("Failed Checks", int(latest_run["failed_checks"]))
    metric_cols[5].metric("Critical Issues", int(latest_run["critical_checks"]))
    metric_cols[6].metric("Open Alerts", unresolved_alert_count(latest_alerts_df))


def render_quality_score_trend(runs_df, alerts_df):
    """Render quality score trend over runs."""

    trend_df = build_quality_trend_frame(runs_df, alerts_df)

    if trend_df.empty:
        st.info("No run history available for trend analysis.")
        return

    available_runs = len(trend_df)
    chart_window = st.sidebar.slider(
        "Trend Runs Shown",
        min_value=1,
        max_value=available_runs,
        value=min(available_runs, 12),
    )
    target_score = st.sidebar.slider(
        "Target Score",
        min_value=0,
        max_value=100,
        value=95,
    )
    chart_df = trend_df.tail(chart_window).copy()

    base = alt.Chart(chart_df).encode(
        x=alt.X(
            "run_label:N",
            title="Run ID",
            sort=list(chart_df["run_label"]),
            axis=alt.Axis(labelAngle=0),
        ),
        tooltip=[
            alt.Tooltip("run_id:O", title="Run ID"),
            alt.Tooltip("quality_score:Q", title="Quality Score", format=".1f"),
            alt.Tooltip("rolling_average:Q", title="3-Run Avg", format=".1f"),
            alt.Tooltip("status:N", title="Status"),
            alt.Tooltip("total_checks:Q", title="Total Checks"),
            alt.Tooltip("passed_checks:Q", title="Passed"),
            alt.Tooltip("failed_checks:Q", title="Failed"),
            alt.Tooltip("critical_checks:Q", title="Critical"),
            alt.Tooltip("alerts:Q", title="Alerts"),
        ],
    )

    bars = base.mark_bar(
        cornerRadiusTopLeft=5,
        cornerRadiusTopRight=5,
    ).encode(
        y=alt.Y(
            "quality_score:Q",
            title="Quality Score (%)",
            scale=alt.Scale(domain=[0, 100]),
        ),
        color=alt.Color(
            "score_band:N",
            title="Score Band",
            scale=alt.Scale(
                domain=["Healthy", "Watch", "Needs attention"],
                range=["#2e7d32", "#f9a825", "#c62828"],
            ),
        ),
    )

    rolling_line = base.mark_line(
        color="#1f77b4",
        strokeWidth=3,
        point=alt.OverlayMarkDef(size=70, filled=True),
    ).encode(
        y=alt.Y("rolling_average:Q", title="Quality Score (%)"),
    )

    target_line = alt.Chart(
        pd.DataFrame({"target": [target_score]})
    ).mark_rule(
        color="#444444",
        strokeDash=[6, 4],
        strokeWidth=2,
    ).encode(
        y="target:Q",
        tooltip=[alt.Tooltip("target:Q", title="Target Score")],
    )

    chart = (
        (bars + rolling_line + target_line)
        .properties(height=360)
        .configure_view(strokeWidth=0)
        .configure_axis(gridColor="#eeeeee", labelColor="#444444", titleColor="#333333")
        .configure_legend(orient="top", title=None)
    )

    st.altair_chart(chart, width="stretch")


def render_failed_by_dataset(results_df):
    """Render failed checks by dataset."""

    if results_df.empty or "status" not in results_df.columns:
        st.info("No failed-check data available.")
        return

    failed_df = results_df[results_df["status"] == "FAIL"]

    if failed_df.empty or "dataset_name" not in failed_df.columns:
        st.success("No failed checks for this selection.")
        return

    chart_df = failed_df.groupby("dataset_name").size().reset_index(name="failed_checks")
    chart = alt.Chart(chart_df).mark_bar(cornerRadiusTopRight=5).encode(
        y=alt.Y("dataset_name:N", title=None, sort="-x"),
        x=alt.X("failed_checks:Q", title="Failed Checks", axis=alt.Axis(format="d")),
        color=alt.value("#c62828"),
        tooltip=[
            alt.Tooltip("dataset_name:N", title="Dataset"),
            alt.Tooltip("failed_checks:Q", title="Failed Checks"),
        ],
    ).properties(height=280).configure_view(strokeWidth=0)

    st.altair_chart(chart, width="stretch")


def render_issues_by_severity(results_df):
    """Render issues by severity."""

    if results_df.empty or "severity" not in results_df.columns:
        st.info("No severity data available.")
        return

    severity_order = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO", "NONE", "UNKNOWN"]
    severity_rank = {severity: index for index, severity in enumerate(severity_order)}
    severity_df = results_df["severity"].value_counts().reset_index()
    severity_df.columns = ["severity", "count"]
    severity_df["severity"] = severity_df["severity"].fillna("UNKNOWN").astype(str).str.upper()
    severity_df.loc[
        ~severity_df["severity"].isin(severity_order),
        "severity",
    ] = "UNKNOWN"
    severity_df = severity_df.groupby("severity", as_index=False)["count"].sum()
    severity_df["severity_rank"] = severity_df["severity"].map(severity_rank)
    severity_df = severity_df.sort_values(["severity_rank", "count"])

    chart = alt.Chart(severity_df).mark_bar(
        cornerRadiusTopRight=5,
        cornerRadiusBottomRight=5,
    ).encode(
        y=alt.Y("severity:N", title=None, sort=severity_order),
        x=alt.X("count:Q", title="Checks", axis=alt.Axis(format="d")),
        color=alt.Color(
            "severity:N",
            legend=None,
            scale=alt.Scale(
                domain=severity_order,
                range=[
                    "#b71c1c",
                    "#e65100",
                    "#f9a825",
                    "#2e7d32",
                    "#1565c0",
                    "#757575",
                    "#9e9e9e",
                ],
            ),
        ),
        tooltip=[
            alt.Tooltip("severity:N", title="Severity"),
            alt.Tooltip("count:Q", title="Checks"),
        ],
    ).properties(height=280).configure_view(strokeWidth=0)

    st.altair_chart(chart, width="stretch")


def render_failed_by_check_type(results_df):
    """Render failed checks grouped by check type."""

    if results_df.empty or "status" not in results_df.columns:
        st.info("No check-type data available.")
        return

    failed_df = results_df[results_df["status"] == "FAIL"]

    if failed_df.empty or "check_type" not in failed_df.columns:
        st.success("No failed check types for this selection.")
        return

    chart_df = failed_df.groupby("check_type").size().reset_index(name="failed_checks")
    chart = alt.Chart(chart_df).mark_bar(cornerRadiusTopRight=5).encode(
        y=alt.Y("check_type:N", title=None, sort="-x"),
        x=alt.X("failed_checks:Q", title="Failed Checks", axis=alt.Axis(format="d")),
        color=alt.value("#455a64"),
        tooltip=[
            alt.Tooltip("check_type:N", title="Check Type"),
            alt.Tooltip("failed_checks:Q", title="Failed Checks"),
        ],
    ).properties(height=280).configure_view(strokeWidth=0)

    st.altair_chart(chart, width="stretch")


def show_dataframe(df, columns=None, empty_message="No records found."):
    """Render a DataFrame with optional column selection."""

    if df.empty:
        st.info(empty_message)
        return

    if columns:
        columns = [column for column in columns if column in df.columns]
        if columns:
            df = df[columns]

    st.dataframe(df, width="stretch", hide_index=True)


def resolve_alert(alert_id):
    """Mark a data quality alert as resolved in PostgreSQL."""

    engine = create_postgres_engine()
    query = text(
        """
        UPDATE data_quality_alerts
        SET is_resolved = TRUE
        WHERE id = :alert_id;
        """
    )

    try:
        with engine.begin() as connection:
            result = connection.execute(query, {"alert_id": int(alert_id)})
        return result.rowcount > 0
    except SQLAlchemyError as exc:
        st.error("Could not resolve the alert. Please check the database connection.")
        st.caption(str(exc))
        return False


def render_alert_resolution_cards(open_alerts):
    """Render one-click resolution controls for unresolved alerts."""

    if open_alerts.empty:
        st.success("No open alerts for this selection.")
        return

    if "id" not in open_alerts.columns:
        st.warning("Alert IDs are missing, so alerts cannot be resolved from the dashboard.")
        return

    display_columns = [
        "id",
        "run_id",
        "alert_type",
        "severity",
        "message",
        "created_at",
    ]
    show_dataframe(open_alerts, columns=display_columns)

    st.markdown("#### Resolve Open Alerts")

    for _, alert in open_alerts.iterrows():
        alert_id = int(alert["id"])
        alert_type = alert.get("alert_type", "Unknown alert")
        severity = alert.get("severity", "UNKNOWN")
        message = alert.get("message", "")

        with st.expander(f"Alert #{alert_id} | {severity} | {alert_type}"):
            st.write(message)

            if st.button("Mark as resolved", key=f"resolve_alert_{alert_id}"):
                if resolve_alert(alert_id):
                    st.success(f"Alert #{alert_id} marked as resolved.")
                    st.rerun()


def render_overview(context):
    st.header("Overview")
    render_metrics(context["latest_run"], context["latest_alerts_df"])
    st.caption(
        f"Latest run time: {context['latest_run'].get('run_time', 'N/A')} | "
        f"Overall status: {context['latest_run'].get('overall_status', 'N/A')}"
    )

    st.divider()
    render_quality_score_trend(context["runs_df"], context["alerts_df"])

    st.divider()
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.subheader("Failed Checks by Dataset")
        render_failed_by_dataset(context["filtered_results"])

    with chart_col2:
        st.subheader("Issues by Severity")
        render_issues_by_severity(context["filtered_results"])

    st.subheader("Failed Checks by Check Type")
    render_failed_by_check_type(context["filtered_results"])

    st.subheader("Latest Run Alerts")
    show_dataframe(
        filter_unresolved_alerts(context["latest_alerts_df"]),
        empty_message="No open alerts for the latest run.",
    )


def render_check_results(context):
    st.header("Check Results")

    tabs = st.tabs(["All Results", "Failed", "Critical", "Anomaly & Drift"])

    with tabs[0]:
        show_dataframe(
            context["filtered_results"],
            empty_message="No check results found for this selection.",
        )

    with tabs[1]:
        failed_df = rows_matching(context["filtered_results"], "status", "FAIL")
        show_dataframe(failed_df, empty_message="No failed checks for this selection.")

    with tabs[2]:
        critical_df = rows_matching(context["filtered_results"], "severity", "CRITICAL")
        show_dataframe(critical_df, empty_message="No critical issues for this selection.")

    with tabs[3]:
        if "check_type" in context["filtered_results"].columns:
            statistical_df = context["filtered_results"][
                context["filtered_results"]["check_type"].isin(STATISTICAL_CHECK_TYPES)
            ]
        else:
            statistical_df = context["filtered_results"].iloc[0:0].copy()
        show_dataframe(
            statistical_df,
            columns=[
                "dataset_name",
                "check_type",
                "column_name",
                "rule",
                "total_rows",
                "failed_rows",
                "failure_rate",
                "status",
                "severity",
                "run_time",
            ],
            empty_message="No anomaly or drift checks found for this selection.",
        )

        if "check_type" in context["filtered_details"].columns:
            statistical_details = context["filtered_details"][
                context["filtered_details"]["check_type"].isin(STATISTICAL_CHECK_TYPES)
            ]
        else:
            statistical_details = context["filtered_details"].iloc[0:0].copy()

        if not statistical_details.empty:
            with st.expander("View anomaly and drift examples"):
                show_dataframe(statistical_details)


def render_issue_details(context):
    st.header("Issue Details")
    show_dataframe(
        context["filtered_details"],
        columns=[
            "dataset_name",
            "check_type",
            "column_name",
            "row_identifier",
            "bad_value",
            "reason",
            "sample_row",
            "created_at",
        ],
        empty_message="No issue details found for this selection.",
    )

    if not context["filtered_details"].empty:
        with st.expander("View raw issue details"):
            show_dataframe(context["filtered_details"])


def render_alerts(context):
    st.header("Alerts")

    selected_alerts = context["filtered_alerts"].copy()

    metric_cols = st.columns(3)
    metric_cols[0].metric("Total Alerts", len(selected_alerts))
    metric_cols[1].metric("Open Alerts", unresolved_alert_count(selected_alerts))
    metric_cols[2].metric(
        "Resolved Alerts",
        max(len(selected_alerts) - unresolved_alert_count(selected_alerts), 0),
    )

    if selected_alerts.empty:
        st.info("No alerts found for the selected run.")
        return

    tabs = st.tabs(["All Alerts", "Open Alerts", "Resolved Alerts", "Edit Alert"])

    with tabs[0]:
        show_dataframe(
            selected_alerts,
            empty_message="No alerts found for the selected run.",
        )

    with tabs[1]:
        open_alerts = filter_unresolved_alerts(selected_alerts)

        if open_alerts.empty:
            st.success("No open alerts for this selection.")
        else:
            show_dataframe(open_alerts)

            st.subheader("Quick Resolve")

            alert_ids = open_alerts["id"].tolist()

            selected_resolve_id = st.selectbox(
                "Select alert to resolve",
                options=alert_ids,
                key="resolve_alert_id",
            )

            if st.button("Mark selected alert as resolved"):
                if resolve_alert(selected_resolve_id):
                    st.success(f"Alert {selected_resolve_id} marked as resolved.")
                    st.rerun()

    with tabs[2]:
        if "is_resolved" not in selected_alerts.columns:
            st.info("Alert resolution column is not available.")
        else:
            resolved_values = selected_alerts["is_resolved"].fillna(False)

            if resolved_values.dtype == object:
                resolved_mask = resolved_values.astype(str).str.lower().isin(
                    ["true", "1", "yes"]
                )
            else:
                resolved_mask = resolved_values == True

            resolved_alerts = selected_alerts[resolved_mask]

            show_dataframe(
                resolved_alerts,
                empty_message="No resolved alerts for this selection.",
            )

    with tabs[3]:
        st.subheader("Edit Alert Data")

        if "id" not in selected_alerts.columns:
            st.warning("Cannot edit alerts because the `id` column is missing.")
            return

        alert_ids = selected_alerts["id"].tolist()

        selected_alert_id = st.selectbox(
            "Select Alert ID",
            options=alert_ids,
            key="edit_alert_id",
        )

        alert_row = selected_alerts[
            selected_alerts["id"] == selected_alert_id
        ].iloc[0]

        severity_options = [
            "CRITICAL",
            "HIGH",
            "MEDIUM",
            "LOW",
            "INFO",
            "NONE",
        ]

        current_severity = str(alert_row.get("severity", "MEDIUM")).upper()

        if current_severity not in severity_options:
            severity_options.append(current_severity)

        current_resolved = alert_row.get("is_resolved", False)

        if isinstance(current_resolved, str):
            current_resolved = current_resolved.lower() in ["true", "1", "yes"]

        with st.form("edit_alert_form"):
            alert_type = st.text_input(
                "Alert Type",
                value=str(alert_row.get("alert_type", "")),
            )

            severity = st.selectbox(
                "Severity",
                options=severity_options,
                index=severity_options.index(current_severity),
            )

            message = st.text_area(
                "Message",
                value=str(alert_row.get("message", "")),
                height=140,
            )

            is_resolved = st.checkbox(
                "Resolved",
                value=bool(current_resolved),
            )

            submitted = st.form_submit_button("Save Alert Changes")

            if submitted:
                if update_alert(
                    alert_id=selected_alert_id,
                    alert_type=alert_type,
                    severity=severity,
                    message=message,
                    is_resolved=is_resolved,
                ):
                    st.success(f"Alert {selected_alert_id} updated successfully.")
                    st.rerun()
def render_data_profiling(context):
    st.header("Data Profiling")
    show_dataframe(
        context["filtered_profiles"],
        columns=[
            "dataset_name",
            "column_name",
            "data_type",
            "total_rows",
            "null_count",
            "null_rate",
            "unique_count",
            "duplicate_count",
            "min_value",
            "max_value",
            "mean",
            "created_at",
        ],
        empty_message="No profiling results found for this selection.",
    )


def render_run_history(context):
    st.header("Run History")
    show_dataframe(
        context["runs_df"],
        empty_message="No run history found.",
    )


def build_sidebar_filters(runs_df, results_df, details_df, alerts_df, profiles_df):
    """Build sidebar navigation and filters."""

    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Section",
        [
            "Overview",
            "Check Results",
            "Issue Details",
            "Alerts",
            "Data Profiling",
            "Run History",
        ],
    )

    st.sidebar.divider()
    st.sidebar.subheader("Filters")

    run_ids = runs_df["run_id"].tolist()
    selected_run_id = st.sidebar.selectbox("Run ID", options=run_ids, index=0)

    run_results = filter_by_value(results_df, "run_id", selected_run_id)
    run_details = filter_by_value(details_df, "run_id", selected_run_id)
    run_alerts = filter_by_value(alerts_df, "run_id", selected_run_id)
    run_profiles = filter_by_value(profiles_df, "run_id", selected_run_id)

    dataset_options = sorted(set(
        unique_options(run_results, "dataset_name")
        + unique_options(run_details, "dataset_name")
        + unique_options(run_profiles, "dataset_name")
    ))
    selected_dataset = st.sidebar.selectbox(
        "Dataset",
        options=["All"] + dataset_options,
    )

    dataset_results = filter_by_value(run_results, "dataset_name", selected_dataset)
    dataset_details = filter_by_value(run_details, "dataset_name", selected_dataset)
    dataset_profiles = filter_by_value(run_profiles, "dataset_name", selected_dataset)

    selected_status = st.sidebar.selectbox(
        "Status",
        options=["All"] + unique_options(dataset_results, "status"),
    )
    selected_severity = st.sidebar.selectbox(
        "Severity",
        options=["All"] + unique_options(dataset_results, "severity"),
    )

    filtered_results = filter_by_value(dataset_results, "status", selected_status)
    filtered_results = filter_by_value(filtered_results, "severity", selected_severity)
    filtered_details = filter_details_by_results(dataset_details, filtered_results)

    return {
        "page": page,
        "selected_run_id": selected_run_id,
        "selected_dataset": selected_dataset,
        "selected_status": selected_status,
        "selected_severity": selected_severity,
        "filtered_results": filtered_results,
        "filtered_details": filtered_details,
        "filtered_alerts": run_alerts,
        "filtered_profiles": dataset_profiles,
    }


def main():
    st.title("Automated Data Quality Monitoring Dashboard")

    runs_df = load_quality_runs()
    results_df = load_quality_results()
    details_df = load_issue_details()
    alerts_df = load_alerts()
    profiles_df = load_profile_results()

    if runs_df.empty or "run_id" not in runs_df.columns:
        st.warning("No data quality runs found. Run `python main.py` first.")
        return

    latest_run = runs_df.iloc[0]
    latest_run_id = int(latest_run["run_id"])
    latest_alerts_df = filter_by_value(alerts_df, "run_id", latest_run_id)

    filters = build_sidebar_filters(
        runs_df,
        results_df,
        details_df,
        alerts_df,
        profiles_df,
    )
    context = {
        "runs_df": runs_df,
        "results_df": results_df,
        "details_df": details_df,
        "alerts_df": alerts_df,
        "profiles_df": profiles_df,
        "latest_run": latest_run,
        "latest_alerts_df": latest_alerts_df,
        **filters,
    }

    pages = {
        "Overview": render_overview,
        "Check Results": render_check_results,
        "Issue Details": render_issue_details,
        "Alerts": render_alerts,
        "Data Profiling": render_data_profiling,
        "Run History": render_run_history,
    }
    pages[filters["page"]](context)


if __name__ == "__main__":
    main()
