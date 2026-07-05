import sys
import json
from datetime import datetime
from io import BytesIO
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
from lineage.lineage_service import get_all_lineage_edges, get_table_lineage
from utils.logger import get_logger


st.set_page_config(
    page_title="Data Quality Monitoring Dashboard",
    layout="wide",
)

logger = get_logger(__name__)

STATISTICAL_CHECK_TYPES = [
    "z_score_anomaly_check",
    "data_drift_check",
    "statistical_check_error",
]


def load_query(query, table_name):
    """Load dashboard data and return an empty DataFrame on table errors."""

    try:
        engine = create_postgres_engine()
        return pd.read_sql(text(query), engine)
    except SQLAlchemyError:
        logger.exception("Could not load dashboard table %s", table_name)
        st.warning(
            f"Could not load `{table_name}`. Run `python database/init_db.py` "
            "if the monitoring tables have not been created yet."
        )
        return pd.DataFrame()
    except Exception:
        logger.exception("Unexpected dashboard load error for %s", table_name)
        st.warning("Could not load dashboard data right now. Please check the logs.")
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


def load_sla_results():
    return load_query(
        """
        SELECT *
        FROM data_quality_sla_results
        ORDER BY id DESC;
        """,
        "data_quality_sla_results",
    )


def update_alert(alert_id, alert_type, severity, message, is_resolved):
    """Update alert information from the dashboard."""

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
        engine = create_postgres_engine()
        with engine.begin() as connection:
            result = connection.execute(
                query,
                {
                    "alert_id": int(alert_id),
                    "alert_type": alert_type,
                    "severity": severity,
                    "message": message,
                    "is_resolved": bool(is_resolved),
                },
            )

        return result.rowcount > 0

    except SQLAlchemyError:
        logger.exception("Could not update alert %s", alert_id)
        st.error("Could not update this alert right now. Please check the logs.")
        return False
    except Exception:
        logger.exception("Unexpected alert update error for %s", alert_id)
        st.error("Could not update this alert right now. Please check the logs.")
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


def load_lineage_edges():
    """Load lineage edges from config/lineage.yaml for dashboard display."""

    try:
        edges = get_all_lineage_edges()
    except Exception:
        logger.exception("Could not load lineage configuration.")
        st.warning("Could not load data lineage configuration. Check config/lineage.yaml.")
        return pd.DataFrame()

    columns = [
        "source_table",
        "source_column",
        "target_table",
        "target_column",
        "relationship_type",
        "description",
        "relationship",
    ]

    return pd.DataFrame(edges, columns=columns)


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


def filter_sla_violations(sla_df):
    """Return SLA rows that did not meet the configured thresholds."""

    if sla_df.empty or "sla_status" not in sla_df.columns:
        return sla_df.iloc[0:0].copy()

    status_values = sla_df["sla_status"].fillna("").astype(str).str.upper()
    return sla_df[status_values != "PASS"]


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


def parse_json_object(value):
    """Parse a JSON object string and return an empty dict on invalid input."""

    if value is None:
        return {}

    if not isinstance(value, (str, bytes)):
        try:
            if pd.isna(value):
                return {}
        except (TypeError, ValueError):
            pass

    try:
        parsed = json.loads(str(value))
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}

    return parsed if isinstance(parsed, dict) else {}


def build_drift_summary(results_df, details_df):
    """Build a readable drift summary from result rows and issue details."""

    if results_df.empty or "check_type" not in results_df.columns:
        return pd.DataFrame()

    drift_results = results_df[results_df["check_type"] == "data_drift_check"].copy()

    if drift_results.empty:
        return pd.DataFrame()

    detail_lookup = {}

    if not details_df.empty and "result_id" in details_df.columns:
        drift_details = details_df[details_df["check_type"] == "data_drift_check"]

        for _, detail in drift_details.iterrows():
            result_id = detail.get("result_id")
            if pd.notna(result_id) and result_id not in detail_lookup:
                detail_lookup[result_id] = detail

    rows = []

    for _, result in drift_results.iterrows():
        detail = detail_lookup.get(result.get("id"))
        payload = {}
        reason = ""

        if detail is not None:
            payload = parse_json_object(detail.get("sample_row"))
            reason = detail.get("reason", "")

        rows.append({
            "dataset_name": result.get("dataset_name"),
            "column_name": result.get("column_name"),
            "drift_method": payload.get("drift_method", "baseline_check"),
            "baseline_value": payload.get("baseline_value"),
            "current_value": payload.get("current_value"),
            "percent_change": payload.get("percent_change"),
            "metric_value": payload.get("metric_value"),
            "threshold": payload.get("threshold"),
            "distribution_difference": payload.get("distribution_difference"),
            "chi_square_p_value": payload.get("chi_square_p_value"),
            "rule": result.get("rule"),
            "status": result.get("status"),
            "severity": result.get("severity"),
            "reason": reason,
        })

    return pd.DataFrame(rows)


def build_sla_trend_frame(sla_df):
    """Prepare SLA pass-rate trend data by run."""

    if sla_df.empty or "run_id" not in sla_df.columns or "sla_status" not in sla_df.columns:
        return pd.DataFrame()

    trend = sla_df.copy()
    trend["sla_status"] = trend["sla_status"].fillna("UNKNOWN").astype(str).str.upper()
    trend["is_pass"] = trend["sla_status"] == "PASS"

    trend_df = (
        trend.groupby("run_id")
        .agg(
            datasets=("dataset_name", "nunique"),
            passed_datasets=("is_pass", "sum"),
            failed_datasets=("is_pass", lambda values: int((~values).sum())),
        )
        .reset_index()
        .sort_values("run_id")
    )
    trend_df["sla_pass_rate"] = (
        trend_df["passed_datasets"] / trend_df["datasets"] * 100
    ).round(2)
    trend_df["run_label"] = trend_df["run_id"].astype(str)

    return trend_df


def lineage_table_options(edges_df):
    """Return table names present in the lineage edge list."""

    if edges_df.empty:
        return []

    tables = set()

    for column in ["source_table", "target_table"]:
        if column in edges_df.columns:
            tables.update(edges_df[column].dropna().astype(str).tolist())

    return sorted(tables)

def render_lineage_matrix(edges_df):
    """Render a lightweight lineage relationship matrix."""

    if edges_df.empty:
        st.info("No lineage relationships found.")
        return

    chart = alt.Chart(edges_df).mark_rect(cornerRadius=4).encode(
        x=alt.X("target_table:N", title="Downstream Table"),
        y=alt.Y("source_table:N", title="Upstream Table"),
        color=alt.Color(
            "relationship_type:N",
            title="Relationship Type",
            scale=alt.Scale(range=["#1565c0", "#2e7d32", "#f9a825", "#6a1b9a"]),
        ),
        tooltip=[
            alt.Tooltip("source_table:N", title="Source Table"),
            alt.Tooltip("source_column:N", title="Source Column"),
            alt.Tooltip("target_table:N", title="Target Table"),
            alt.Tooltip("target_column:N", title="Target Column"),
            alt.Tooltip("relationship_type:N", title="Type"),
            alt.Tooltip("description:N", title="Description"),
        ],
    ).properties(height=260)

    labels = alt.Chart(edges_df).mark_text(
        color="white",
        fontSize=12,
        fontWeight="bold",
    ).encode(
        x=alt.X("target_table:N"),
        y=alt.Y("source_table:N"),
        text=alt.Text("relationship_type:N"),
    )

    layered_chart = (
        alt.layer(chart, labels)
        .configure_view(strokeWidth=0)
    )

    st.altair_chart(layered_chart, width="stretch")

def build_lineage_failure_map(results_df, details_df, edges_df):
    """Map failed referential integrity checks to lineage edges."""

    if results_df.empty or edges_df.empty or "check_type" not in results_df.columns:
        return pd.DataFrame()

    failed_checks = results_df[
        (results_df["check_type"] == "referential_integrity_check")
        & (results_df["status"] == "FAIL")
    ].copy()

    if failed_checks.empty:
        return pd.DataFrame()

    detail_lookup = {}

    if (
        not details_df.empty
        and "result_id" in details_df.columns
        and "check_type" in details_df.columns
    ):
        ri_details = details_df[
            details_df["check_type"] == "referential_integrity_check"
        ]

        for _, detail in ri_details.iterrows():
            result_id = detail.get("result_id")
            if pd.notna(result_id) and result_id not in detail_lookup:
                detail_lookup[result_id] = detail

    rows = []

    for _, check in failed_checks.iterrows():
        dataset_name = check.get("dataset_name")
        column_name = check.get("column_name")
        matching_edges = edges_df[
            (
                (edges_df["target_table"] == dataset_name)
                & (edges_df["target_column"] == column_name)
            )
            | (
                (edges_df["source_table"] == dataset_name)
                & (edges_df["source_column"] == column_name)
            )
        ]

        if matching_edges.empty:
            matching_edges = pd.DataFrame([{
                "source_table": None,
                "source_column": None,
                "target_table": dataset_name,
                "target_column": column_name,
                "relationship_type": "unmapped",
                "description": "No matching lineage relationship found.",
            }])

        detail = detail_lookup.get(check.get("id"))

        for _, edge in matching_edges.iterrows():
            rows.append({
                "run_id": check.get("run_id"),
                "dataset_name": dataset_name,
                "check_column": column_name,
                "source": (
                    f"{edge.get('source_table')}.{edge.get('source_column')}"
                    if edge.get("source_table")
                    else None
                ),
                "target": (
                    f"{edge.get('target_table')}.{edge.get('target_column')}"
                    if edge.get("target_table")
                    else None
                ),
                "relationship_type": edge.get("relationship_type"),
                "failed_rows": check.get("failed_rows"),
                "severity": check.get("severity"),
                "reason": detail.get("reason", "") if detail is not None else "",
                "description": edge.get("description"),
            })

    return pd.DataFrame(rows)


def safe_filename_part(value):
    """Return a filesystem-friendly piece for export filenames."""

    text_value = str(value).strip() if value not in (None, "") else "all"
    return "".join(
        character if character.isalnum() or character in ("-", "_") else "_"
        for character in text_value
    )


def build_export_filename(stem, run_id, extension, timestamp):
    """Build an export filename with run ID and date/time."""

    return (
        f"{safe_filename_part(stem)}_run_{safe_filename_part(run_id)}_"
        f"{timestamp}.{extension}"
    )


def dataframe_to_csv_bytes(df):
    """Convert a DataFrame to CSV bytes for Streamlit downloads."""

    return df.to_csv(index=False).encode("utf-8")


def render_csv_download(container, label, df, stem, context, key):
    """Render a CSV download button for the provided DataFrame."""

    run_id = context.get("selected_run_id", "all")
    timestamp = context.get("export_timestamp", datetime.now().strftime("%Y%m%d_%H%M%S"))
    file_name = build_export_filename(stem, run_id, "csv", timestamp)
    export_df = df.copy() if isinstance(df, pd.DataFrame) else pd.DataFrame()

    container.download_button(
        label=label,
        data=dataframe_to_csv_bytes(export_df),
        file_name=file_name,
        mime="text/csv",
        key=key,
        disabled=export_df.empty,
    )


def build_excel_report(context):
    """Create an Excel workbook containing the current dashboard report data."""

    output = BytesIO()
    selected_run = filter_by_value(
        context["runs_df"],
        "run_id",
        context["selected_run_id"],
    )
    sheets = {
        "Run Summary": selected_run,
        "Check Results": context["filtered_results"],
        "Issue Details": context["filtered_details"],
        "Alerts": context["filtered_alerts"],
        "SLA Results": context.get("filtered_sla", pd.DataFrame()),
    }

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for sheet_name, df in sheets.items():
            export_df = df.copy() if isinstance(df, pd.DataFrame) else pd.DataFrame()
            if export_df.empty:
                export_df = pd.DataFrame({"message": ["No records for this selection."]})
            export_df.to_excel(writer, sheet_name=sheet_name, index=False)

    output.seek(0)
    return output.getvalue()


def render_dashboard_exports(context):
    """Render dashboard-wide report download controls."""

    st.sidebar.divider()
    with st.sidebar.expander("Downloads", expanded=False) as export_panel:
        render_csv_download(
            export_panel,
            "Check results CSV",
            context["filtered_results"],
            "check_results",
            context,
            "download_check_results_csv",
        )
        render_csv_download(
            export_panel,
            "Issue details CSV",
            context["filtered_details"],
            "issue_details",
            context,
            "download_issue_details_csv",
        )
        render_csv_download(
            export_panel,
            "Alerts CSV",
            context["filtered_alerts"],
            "alerts",
            context,
            "download_alerts_csv",
        )
        render_csv_download(
            export_panel,
            "SLA results CSV",
            context.get("filtered_sla", pd.DataFrame()),
            "sla_results",
            context,
            "download_sla_results_csv",
        )
        render_csv_download(
            export_panel,
            "Run history CSV",
            context["runs_df"],
            "run_history",
            context,
            "download_run_history_csv",
        )

        try:
            excel_data = build_excel_report(context)
        except ImportError:
            logger.exception("openpyxl is not installed for Excel export")
            export_panel.info("Excel export needs `openpyxl`. Install requirements and reload.")
            return
        except Exception:
            logger.exception("Could not build dashboard Excel export")
            export_panel.info("Excel export is unavailable right now. Please check the logs.")
            return

        timestamp = context.get("export_timestamp", datetime.now().strftime("%Y%m%d_%H%M%S"))
        file_name = build_export_filename(
            "data_quality_report",
            context.get("selected_run_id", "all"),
            "xlsx",
            timestamp,
        )
        export_panel.download_button(
            label="Excel report",
            data=excel_data,
            file_name=file_name,
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            key="download_excel_report",
        )


def resolve_alert(alert_id):
    """Mark a data quality alert as resolved in PostgreSQL."""

    query = text(
        """
        UPDATE data_quality_alerts
        SET is_resolved = TRUE
        WHERE id = :alert_id;
        """
    )

    try:
        engine = create_postgres_engine()
        with engine.begin() as connection:
            result = connection.execute(query, {"alert_id": int(alert_id)})
        return result.rowcount > 0
    except SQLAlchemyError:
        logger.exception("Could not resolve alert %s", alert_id)
        st.error("Could not resolve this alert right now. Please check the logs.")
        return False
    except Exception:
        logger.exception("Unexpected alert resolution error for %s", alert_id)
        st.error("Could not resolve this alert right now. Please check the logs.")
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

        drift_summary = build_drift_summary(
            context["filtered_results"],
            context["filtered_details"],
        )

        st.subheader("Drift Detection")
        show_dataframe(
            drift_summary,
            columns=[
                "dataset_name",
                "column_name",
                "drift_method",
                "baseline_value",
                "current_value",
                "percent_change",
                "metric_value",
                "threshold",
                "distribution_difference",
                "chi_square_p_value",
                "status",
                "severity",
                "reason",
            ],
            empty_message="No drift detection results found for this selection.",
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
    open_alerts = filter_unresolved_alerts(selected_alerts)
    resolved_alerts = filter_resolved_alerts(selected_alerts)

    metric_cols = st.columns(3)
    metric_cols[0].metric("Total Alerts", len(selected_alerts))
    metric_cols[1].metric("Open Alerts", len(open_alerts))
    metric_cols[2].metric("Resolved Alerts", len(resolved_alerts))

    if context.get("selected_alert_severity") != "All":
        st.caption(f"Alert severity filter: {context['selected_alert_severity']}")

    if selected_alerts.empty:
        st.info("No alerts found for the selected run.")
        return

    tabs = st.tabs(["Unresolved Alerts", "Resolved Alerts", "All Alerts", "Edit Alert"])

    with tabs[0]:
        render_alert_resolution_cards(open_alerts)

    with tabs[1]:
        show_dataframe(
            resolved_alerts,
            empty_message="No resolved alerts for this selection.",
        )

    with tabs[2]:
        show_dataframe(
            selected_alerts,
            empty_message="No alerts found for the selected run.",
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
            "std_dev",
            "created_at",
        ],
        empty_message="No profiling results found for this selection.",
    )


def render_data_lineage(context):
    st.header("Data Lineage")

    edges_df = context["lineage_edges_df"]

    if edges_df.empty:
        st.info("No lineage configuration found. Add relationships to config/lineage.yaml.")
        return

    table_options = lineage_table_options(edges_df)
    default_table = context.get("selected_dataset")

    if default_table not in table_options:
        default_table = "All"

    selected_table = st.selectbox(
        "Lineage Table",
        options=["All"] + table_options,
        index=(["All"] + table_options).index(default_table),
    )

    active_edges = edges_df.copy()

    if selected_table != "All":
        active_edges = edges_df[
            (edges_df["source_table"] == selected_table)
            | (edges_df["target_table"] == selected_table)
        ]

    failed_lineage_df = build_lineage_failure_map(
        context["filtered_results"],
        context["filtered_details"],
        edges_df,
    )

    if selected_table != "All" and not failed_lineage_df.empty:
        selected_token = f"{selected_table}."
        failed_lineage_df = failed_lineage_df[
            failed_lineage_df["source"].fillna("").str.startswith(selected_token)
            | failed_lineage_df["target"].fillna("").str.startswith(selected_token)
            | (failed_lineage_df["dataset_name"] == selected_table)
        ]

    metric_cols = st.columns(3)
    metric_cols[0].metric("Lineage Tables", len(table_options))
    metric_cols[1].metric("Relationships", len(active_edges))
    metric_cols[2].metric("Failed Lineage Checks", len(failed_lineage_df))

    st.subheader("Relationship Matrix")
    render_lineage_matrix(active_edges)

    if selected_table != "All":
        table_lineage = get_table_lineage(selected_table)
        st.caption(
            f"{table_lineage.get('description', 'No description')} | "
            f"Primary key: {table_lineage.get('primary_key') or 'N/A'}"
        )

        upstream_col, downstream_col = st.columns(2)

        with upstream_col:
            st.subheader("Upstream Dependencies")
            show_dataframe(
                pd.DataFrame(table_lineage["upstream"]),
                columns=[
                    "source_table",
                    "source_column",
                    "target_table",
                    "target_column",
                    "relationship_type",
                    "description",
                ],
                empty_message="No upstream dependencies configured.",
            )

        with downstream_col:
            st.subheader("Downstream Dependencies")
            show_dataframe(
                pd.DataFrame(table_lineage["downstream"]),
                columns=[
                    "source_table",
                    "source_column",
                    "target_table",
                    "target_column",
                    "relationship_type",
                    "description",
                ],
                empty_message="No downstream dependencies configured.",
            )

    st.subheader("Lineage Relationships")
    show_dataframe(
        active_edges,
        columns=[
            "source_table",
            "source_column",
            "target_table",
            "target_column",
            "relationship_type",
            "description",
            "relationship",
        ],
        empty_message="No lineage relationships found for this selection.",
    )

    st.subheader("Failed Checks Mapped To Lineage")
    show_dataframe(
        failed_lineage_df,
        columns=[
            "run_id",
            "dataset_name",
            "check_column",
            "source",
            "target",
            "relationship_type",
            "failed_rows",
            "severity",
            "reason",
            "description",
        ],
        empty_message="No failed referential integrity checks for this lineage selection.",
    )


def render_sla_tracking(context):
    st.header("SLA Tracking")

    selected_sla = context["filtered_sla"].copy()
    historical_sla = filter_by_value(
        context["sla_df"],
        "dataset_name",
        context.get("selected_dataset", "All"),
    )
    selected_violations = filter_sla_violations(selected_sla)
    historical_violations = filter_sla_violations(historical_sla)

    if selected_sla.empty:
        st.info("No SLA results found for this selection.")
    else:
        status_values = selected_sla["sla_status"].fillna("").astype(str).str.upper()
        quality_values = pd.to_numeric(
            selected_sla.get("actual_quality_score", pd.Series(dtype=float)),
            errors="coerce",
        )
        avg_quality_score = quality_values.mean()
        metric_cols = st.columns(4)
        metric_cols[0].metric("Datasets Evaluated", len(selected_sla))
        metric_cols[1].metric("SLA Met", int((status_values == "PASS").sum()))
        metric_cols[2].metric("SLA Violations", len(selected_violations))
        metric_cols[3].metric(
            "Avg Quality Score",
            "N/A" if pd.isna(avg_quality_score) else f"{avg_quality_score:.1f}%",
        )

    st.subheader("Selected Run SLA Status")
    show_dataframe(
        selected_sla,
        columns=[
            "run_id",
            "dataset_name",
            "minimum_quality_score",
            "actual_quality_score",
            "max_critical_issues",
            "actual_critical_issues",
            "max_failed_checks",
            "actual_failed_checks",
            "sla_status",
            "reason",
            "created_at",
        ],
        empty_message="No SLA status rows found for this run.",
    )

    st.subheader("SLA Trend Over Runs")
    trend_df = build_sla_trend_frame(historical_sla)

    if trend_df.empty:
        st.info("No historical SLA trend data available.")
    else:
        chart = alt.Chart(trend_df).mark_line(
            color="#1565c0",
            strokeWidth=3,
            point=alt.OverlayMarkDef(size=80, filled=True),
        ).encode(
            x=alt.X(
                "run_label:N",
                title="Run ID",
                sort=list(trend_df["run_label"]),
                axis=alt.Axis(labelAngle=0),
            ),
            y=alt.Y(
                "sla_pass_rate:Q",
                title="SLA Pass Rate (%)",
                scale=alt.Scale(domain=[0, 100]),
            ),
            tooltip=[
                alt.Tooltip("run_id:O", title="Run ID"),
                alt.Tooltip("sla_pass_rate:Q", title="SLA Pass Rate", format=".1f"),
                alt.Tooltip("datasets:Q", title="Datasets"),
                alt.Tooltip("passed_datasets:Q", title="SLA Met"),
                alt.Tooltip("failed_datasets:Q", title="Violations"),
            ],
        ).properties(height=320).configure_view(strokeWidth=0)

        st.altair_chart(chart, width="stretch")

    st.subheader("Historical SLA Violations")
    show_dataframe(
        historical_violations,
        columns=[
            "run_id",
            "dataset_name",
            "actual_quality_score",
            "minimum_quality_score",
            "actual_critical_issues",
            "max_critical_issues",
            "actual_failed_checks",
            "max_failed_checks",
            "sla_status",
            "reason",
            "created_at",
        ],
        empty_message="No SLA violations found for this dataset selection.",
    )


def render_run_history(context):
    st.header("Run History")
    show_dataframe(
        context["runs_df"],
        empty_message="No run history found.",
    )


def build_sidebar_filters(
    runs_df,
    results_df,
    details_df,
    alerts_df,
    profiles_df,
    sla_df,
    lineage_edges_df,
):
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
            "Data Lineage",
            "SLA Tracking",
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
    run_sla = filter_by_value(sla_df, "run_id", selected_run_id)

    dataset_options = sorted(set(
        unique_options(run_results, "dataset_name")
        + unique_options(run_details, "dataset_name")
        + unique_options(run_profiles, "dataset_name")
        + unique_options(run_sla, "dataset_name")
        + lineage_table_options(lineage_edges_df)
    ))
    selected_dataset = st.sidebar.selectbox(
        "Dataset",
        options=["All"] + dataset_options,
    )

    dataset_results = filter_by_value(run_results, "dataset_name", selected_dataset)
    dataset_details = filter_by_value(run_details, "dataset_name", selected_dataset)
    dataset_profiles = filter_by_value(run_profiles, "dataset_name", selected_dataset)
    dataset_sla = filter_by_value(run_sla, "dataset_name", selected_dataset)

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

    selected_alert_severity = st.sidebar.selectbox(
        "Alert Severity",
        options=["All"] + unique_options(run_alerts, "severity"),
    )
    filtered_alerts = filter_by_value(run_alerts, "severity", selected_alert_severity)

    return {
        "page": page,
        "selected_run_id": selected_run_id,
        "selected_dataset": selected_dataset,
        "selected_status": selected_status,
        "selected_severity": selected_severity,
        "selected_alert_severity": selected_alert_severity,
        "filtered_results": filtered_results,
        "filtered_details": filtered_details,
        "filtered_alerts": filtered_alerts,
        "filtered_profiles": dataset_profiles,
        "filtered_sla": dataset_sla,
    }


def main():
    st.title("Automated Data Quality Monitoring Dashboard")

    runs_df = load_quality_runs()
    results_df = load_quality_results()
    details_df = load_issue_details()
    alerts_df = load_alerts()
    profiles_df = load_profile_results()
    sla_df = load_sla_results()
    lineage_edges_df = load_lineage_edges()

    if runs_df.empty or "run_id" not in runs_df.columns:
        st.warning("No data quality runs found. Run `python main.py` first.")
        render_data_lineage({
            "lineage_edges_df": lineage_edges_df,
            "filtered_results": pd.DataFrame(),
            "filtered_details": pd.DataFrame(),
            "selected_dataset": "All",
        })
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
        sla_df,
        lineage_edges_df,
    )
    context = {
        "runs_df": runs_df,
        "results_df": results_df,
        "details_df": details_df,
        "alerts_df": alerts_df,
        "profiles_df": profiles_df,
        "sla_df": sla_df,
        "lineage_edges_df": lineage_edges_df,
        "latest_run": latest_run,
        "latest_alerts_df": latest_alerts_df,
        "export_timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
        **filters,
    }
    render_dashboard_exports(context)

    pages = {
        "Overview": render_overview,
        "Check Results": render_check_results,
        "Issue Details": render_issue_details,
        "Alerts": render_alerts,
        "Data Profiling": render_data_profiling,
        "Data Lineage": render_data_lineage,
        "SLA Tracking": render_sla_tracking,
        "Run History": render_run_history,
    }
    pages[filters["page"]](context)


if __name__ == "__main__":
    main()
