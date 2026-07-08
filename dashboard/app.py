import sys
import json
import subprocess
from datetime import datetime
from html import escape
from io import BytesIO
from pathlib import Path
from urllib.parse import quote

import altair as alt
import pandas as pd
import streamlit as st
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from auth.dashboard_auth import clear_dashboard_login_state, require_dashboard_login
from dashboard.actions import run_checks_subprocess
from dashboard.permissions import (
    can_edit_alerts_for_role,
    can_export_reports,
    can_resolve_alerts_for_role,
    can_run_checks,
)
from data_sources.postgres_connector import create_monitor_engine
from lineage.lineage_service import get_all_lineage_edges, get_table_lineage
from reports.export_reports import export_run_to_excel, export_run_to_pdf
from rules.rules_catalog import (
    flatten_rules_for_display,
    load_rules_catalog,
    rules_to_yaml,
)
from ui.charts import (
    apply_enterprise_chart_theme,
    score_band_color_scale,
    severity_color_scale,
)
from ui.components import (
    add_badge_columns,
    alert_status_badge,
    empty_state,
    error_state,
    metric_card,
    render_footer,
    section_header,
    severity_badge,
    sla_badge,
    status_badge,
    warning_state,
)
from ui.theme import (
    get_brand_config,
    get_version,
    inject_enterprise_css,
    render_app_header,
    render_sidebar_branding,
)
from utils.logger import get_logger
from utils.config_validator import validate_config
from utils.audit_logger import log_audit_event


BRAND = get_brand_config()

st.set_page_config(
    page_title=BRAND.dashboard_title,
    page_icon=BRAND.dashboard_icon,
    layout="wide",
)

logger = get_logger(__name__)

inject_enterprise_css()

if not require_dashboard_login():
    st.stop()

STATISTICAL_CHECK_TYPES = [
    "z_score_anomaly_check",
    "data_drift_check",
    "statistical_check_error",
]

DISPLAY_COLUMN_NAMES = {
    "id": "ID",
    "run_id": "Run ID",
    "run_time": "Run Time",
    "dataset_name": "Dataset",
    "check_type": "Check Type",
    "column_name": "Column",
    "rule": "Rule",
    "total_rows": "Total Rows",
    "failed_rows": "Failed Rows",
    "failure_rate": "Failure Rate",
    "status": "Status",
    "status_display": "Status Label",
    "severity": "Severity",
    "severity_display": "Severity Label",
    "row_identifier": "Row",
    "bad_value": "Bad Value",
    "reason": "Reason",
    "sample_row": "Sample Row",
    "alert_type": "Alert Type",
    "owner_team": "Owner Team",
    "owner_email": "Owner Email",
    "assigned_to": "Assigned To",
    "message": "Message",
    "is_resolved": "Resolved",
    "alert_state": "Alert State",
    "resolution_notes": "Resolution Notes",
    "resolved_at": "Resolved At",
    "sla_due_at": "SLA Due At",
    "escalation_status": "Escalation Status",
    "escalated_at": "Escalated At",
    "escalation_level": "Escalation Level",
    "created_at": "Created At",
    "column": "Column",
    "data_type": "Data Type",
    "null_count": "Null Count",
    "null_rate": "Null Rate",
    "unique_count": "Unique Count",
    "duplicate_count": "Duplicate Count",
    "min_value": "Min",
    "max_value": "Max",
    "mean": "Mean",
    "std_dev": "Std Dev",
    "sla_status": "SLA Status",
    "sla_display": "SLA Label",
    "actual_quality_score": "Actual Score",
    "minimum_quality_score": "Minimum Score",
    "actual_critical_issues": "Critical Issues",
    "max_critical_issues": "Critical Limit",
    "actual_failed_checks": "Failed Checks",
    "max_failed_checks": "Failed Limit",
    "row_count": "Row Count",
    "baseline_row_count": "Baseline Row Count",
    "percent_change": "Percent Change",
    "rule_type": "Rule Type",
    "rule_config": "Rule Config",
    "enabled": "Enabled",
    "event_type": "Event Type",
    "username": "Username",
    "role": "Role",
    "entity_type": "Entity Type",
    "entity_id": "Entity ID",
    "old_value": "Old Value",
    "new_value": "New Value",
    "ip_address": "IP Address",
}


def dashboard_username():
    """Return the current dashboard username for audit events."""

    return st.session_state.get("dashboard_authenticated_user", "anonymous")


def log_dashboard_event(
    event_type,
    entity_type=None,
    entity_id=None,
    old_value=None,
    new_value=None,
) -> bool:
    """Record a dashboard audit event with current user context."""

    return log_audit_event(
        event_type=event_type,
        username=dashboard_username(),
        role=current_user_role(),
        entity_type=entity_type,
        entity_id=entity_id,
        old_value=old_value,
        new_value=new_value,
    )


def load_query(query, table_name):
    """Load dashboard data and return an empty DataFrame on table errors."""

    try:
        engine = create_monitor_engine()
        return pd.read_sql(text(query), engine)
    except SQLAlchemyError:
        logger.exception("Could not load dashboard table %s", table_name)
        warning_state(
            "Monitoring table is not available",
            f"Could not load {table_name}. Initialize the monitoring database and refresh.",
        )
        st.code("python database/init_db.py", language="powershell")
        return pd.DataFrame()
    except Exception:
        logger.exception("Unexpected dashboard load error for %s", table_name)
        error_state(
            "Dashboard data could not be loaded",
            "Please check the application logs and database connection settings.",
            "python cli.py init-db",
        )
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


def load_audit_logs():
    return load_query(
        """
        SELECT *
        FROM audit_logs
        ORDER BY created_at DESC, id DESC;
        """,
        "audit_logs",
    )


def update_alert(
    alert_id,
    alert_type,
    severity,
    message,
    is_resolved,
    owner_team="",
    owner_email="",
    assigned_to="",
    resolution_notes="",
):
    """Update alert information from the dashboard."""

    query = text("""
        UPDATE data_quality_alerts
        SET
            alert_type = :alert_type,
            severity = :severity,
            message = :message,
            owner_team = :owner_team,
            owner_email = :owner_email,
            assigned_to = :assigned_to,
            resolution_notes = :resolution_notes,
            is_resolved = :is_resolved,
            resolved_at = CASE
                WHEN :is_resolved THEN COALESCE(resolved_at, CURRENT_TIMESTAMP)
                ELSE NULL
            END
        WHERE id = :alert_id;
    """)

    try:
        engine = create_monitor_engine()
        with engine.begin() as connection:
            result = connection.execute(
                query,
                {
                    "alert_id": int(alert_id),
                    "alert_type": alert_type,
                    "severity": severity,
                    "message": message,
                    "owner_team": owner_team,
                    "owner_email": owner_email,
                    "assigned_to": assigned_to,
                    "resolution_notes": resolution_notes,
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


def load_volume_history():
    return load_query(
        """
        SELECT *
        FROM data_volume_history
        ORDER BY run_id DESC, id DESC;
        """,
        "data_volume_history",
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


def load_dashboard_rules_catalog():
    """Load active rules and flatten them for dashboard display."""

    try:
        rules = load_rules_catalog()
        rows = flatten_rules_for_display(rules)
    except Exception:
        logger.exception("Could not load rules catalog.")
        st.warning("Could not load active rules from config/rules.yaml.")
        return {}, pd.DataFrame()

    return rules, pd.DataFrame(rows)


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


def form_text_value(value):
    """Return a clean string value for Streamlit form inputs."""

    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass

    return str(value)


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


def _status_to_card(status):
    """Map a status value to metric card styling."""

    normalized = str(status or "").upper()
    if normalized in {"PASS", "RESOLVED"}:
        return "success"
    if normalized in {"FAIL", "CRITICAL", "HIGH"}:
        return "error"
    if normalized in {"WARNING", "MEDIUM"}:
        return "warning"
    return "neutral"


def _count_status(value):
    """Return card status based on whether a count is zero."""

    try:
        return "success" if int(value) == 0 else "error"
    except (TypeError, ValueError):
        return "neutral"


def current_user_role():
    """Return the current dashboard role when auth roles are available."""

    return st.session_state.get("dashboard_role", "admin")


def can_edit_alerts():
    """Return whether the current role can edit alerts."""

    return can_edit_alerts_for_role(current_user_role())


def can_resolve_alerts():
    """Return whether the current role can resolve alerts."""

    return can_resolve_alerts_for_role(current_user_role())


def can_export_current_reports():
    """Return whether the current role can export executive reports."""

    return can_export_reports(current_user_role())


def can_run_dashboard_checks():
    """Return whether the current role can trigger checks."""

    return can_run_checks(current_user_role())


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


def render_metrics(latest_run, latest_alerts_df, latest_sla_df=None):
    """Render latest-run KPI cards."""

    latest_sla_df = latest_sla_df if latest_sla_df is not None else pd.DataFrame()
    sla_status = "UNKNOWN"

    if not latest_sla_df.empty and "sla_status" in latest_sla_df.columns:
        statuses = latest_sla_df["sla_status"].fillna("UNKNOWN").astype(str).str.upper()
        sla_status = "FAIL" if (statuses != "PASS").any() else "PASS"

    quality_score = latest_run.get("quality_score", 0)
    overall_status = latest_run.get("overall_status", "UNKNOWN")
    open_alerts = unresolved_alert_count(latest_alerts_df)

    metric_cols = st.columns(6)
    with metric_cols[0]:
        metric_card(
            "Quality Score",
            f"{quality_score}%",
            "Weighted pass rate across checks",
            "success" if float(quality_score) >= 90 else "warning",
        )
    with metric_cols[1]:
        metric_card("Overall Status", overall_status, "Latest monitoring run", _status_to_card(overall_status))
    with metric_cols[2]:
        metric_card("Total Checks", int(latest_run["total_checks"]), "Executed checks", "info")
    with metric_cols[3]:
        metric_card("Failed Checks", int(latest_run["failed_checks"]), "Requires review", _count_status(latest_run["failed_checks"]))
    with metric_cols[4]:
        metric_card("Critical Issues", int(latest_run["critical_checks"]), "Highest priority", _count_status(latest_run["critical_checks"]))
    with metric_cols[5]:
        metric_card(
            "Open Alerts",
            open_alerts,
            f"SLA {sla_status}",
            _count_status(open_alerts),
        )


def render_quality_score_trend(runs_df, alerts_df):
    """Render quality score trend over runs."""

    trend_df = build_quality_trend_frame(runs_df, alerts_df)

    if trend_df.empty:
        empty_state(
            "No trend data yet",
            "Run data quality checks to start building quality score history.",
            "python cli.py run-checks",
        )
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
            scale=score_band_color_scale(),
        ),
    )

    rolling_line = base.mark_line(
        color=BRAND.accent_color,
        strokeWidth=2.5,
        point=alt.OverlayMarkDef(size=58, filled=True),
    ).encode(
        y=alt.Y("rolling_average:Q", title="Quality Score (%)"),
    )

    target_line = alt.Chart(
        pd.DataFrame({"target": [target_score]})
    ).mark_rule(
        color="#94A3B8",
        strokeDash=[6, 4],
        strokeWidth=1.5,
    ).encode(
        y="target:Q",
        tooltip=[alt.Tooltip("target:Q", title="Target Score")],
    )

    chart = apply_enterprise_chart_theme(bars + rolling_line + target_line, height=360)

    st.altair_chart(chart, width="stretch")


def render_failed_by_dataset(results_df):
    """Render failed checks by dataset."""

    if results_df.empty or "status" not in results_df.columns:
        empty_state("No failed-check data", "No check result rows are available for this selection.")
        return

    failed_df = results_df[results_df["status"] == "FAIL"]

    if failed_df.empty or "dataset_name" not in failed_df.columns:
        empty_state("No failed checks", "This selection has no failed checks.")
        return

    chart_df = failed_df.groupby("dataset_name").size().reset_index(name="failed_checks")
    chart = alt.Chart(chart_df).mark_bar(
        cornerRadiusTopRight=5,
        cornerRadiusBottomRight=5,
        opacity=0.9,
    ).encode(
        y=alt.Y("dataset_name:N", title=None, sort="-x"),
        x=alt.X("failed_checks:Q", title="Failed Checks", axis=alt.Axis(format="d")),
        color=alt.value("#DC2626"),
        tooltip=[
            alt.Tooltip("dataset_name:N", title="Dataset"),
            alt.Tooltip("failed_checks:Q", title="Failed Checks"),
        ],
    )

    st.altair_chart(apply_enterprise_chart_theme(chart, height=280), width="stretch")


def render_issues_by_severity(results_df):
    """Render issues by severity."""

    if results_df.empty or "severity" not in results_df.columns:
        empty_state("No severity data", "No severity values are available for this selection.")
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
            scale=severity_color_scale(),
        ),
        tooltip=[
            alt.Tooltip("severity:N", title="Severity"),
            alt.Tooltip("count:Q", title="Checks"),
        ],
    )

    st.altair_chart(apply_enterprise_chart_theme(chart, height=280), width="stretch")


def render_failed_by_check_type(results_df):
    """Render failed checks grouped by check type."""

    if results_df.empty or "status" not in results_df.columns:
        empty_state("No check-type data", "No check-type results are available for this selection.")
        return

    failed_df = results_df[results_df["status"] == "FAIL"]

    if failed_df.empty or "check_type" not in failed_df.columns:
        empty_state("No failed check types", "This selection has no failed check types.")
        return

    chart_df = failed_df.groupby("check_type").size().reset_index(name="failed_checks")
    chart = alt.Chart(chart_df).mark_bar(
        cornerRadiusTopRight=5,
        cornerRadiusBottomRight=5,
        opacity=0.85,
    ).encode(
        y=alt.Y("check_type:N", title=None, sort="-x"),
        x=alt.X("failed_checks:Q", title="Failed Checks", axis=alt.Axis(format="d")),
        color=alt.value("#DC2626"),
        tooltip=[
            alt.Tooltip("check_type:N", title="Check Type"),
            alt.Tooltip("failed_checks:Q", title="Failed Checks"),
        ],
    )

    st.altair_chart(apply_enterprise_chart_theme(chart, height=280), width="stretch")


def show_dataframe(df, columns=None, empty_message="No records found.", height=420):
    """Render a DataFrame with optional column selection."""

    if df.empty:
        empty_state("No records found", empty_message)
        return

    full_source_df = add_badge_columns(df.copy())
    df = full_source_df.copy()

    if columns:
        enhanced_columns = []
        for column in columns:
            enhanced_columns.append(column)
            if column == "status" and "status_display" in df.columns:
                enhanced_columns.append("status_display")
            if column == "severity" and "severity_display" in df.columns:
                enhanced_columns.append("severity_display")
            if column == "sla_status" and "sla_display" in df.columns:
                enhanced_columns.append("sla_display")
            if column == "is_resolved" and "alert_state" in df.columns:
                enhanced_columns.append("alert_state")
        columns = enhanced_columns
        columns = [column for column in columns if column in df.columns]
        if columns:
            df = df[columns]

    summary_df = _friendly_dataframe(df)
    full_df = _friendly_dataframe(full_source_df)

    tabs = st.tabs(["Summary View", "Full Data"])
    with tabs[0]:
        st.dataframe(summary_df, width="stretch", hide_index=True, height=height)
    with tabs[1]:
        with st.expander("View complete raw table", expanded=False):
            st.dataframe(full_df, width="stretch", hide_index=True, height=max(height, 480))


def _friendly_dataframe(df):
    """Return a dataframe with user-friendly display column names."""

    return df.rename(columns={
        column: DISPLAY_COLUMN_NAMES.get(column, column.replace("_", " ").title())
        for column in df.columns
    })


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


def build_schema_drift_summary(details_df):
    """Build a readable schema drift summary from issue detail rows."""

    if details_df.empty or "check_type" not in details_df.columns:
        return pd.DataFrame()

    schema_details = details_df[details_df["check_type"] == "schema_drift_check"]
    rows = []

    for _, detail in schema_details.iterrows():
        payload = parse_json_object(detail.get("sample_row"))
        previous_schema = payload.get("previous_schema") or {}
        current_schema = payload.get("current_schema") or {}
        rows.append({
            "dataset_name": detail.get("dataset_name"),
            "column_name": detail.get("column_name"),
            "change_type": payload.get("change_type"),
            "previous_data_type": previous_schema.get("data_type"),
            "current_data_type": current_schema.get("data_type"),
            "previous_nullable": previous_schema.get("is_nullable"),
            "current_nullable": current_schema.get("is_nullable"),
            "previous_position": previous_schema.get("ordinal_position"),
            "current_position": current_schema.get("ordinal_position"),
            "reason": detail.get("reason"),
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
        empty_state("No lineage relationships", "No configured lineage relationships were found.")
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

    st.altair_chart(apply_enterprise_chart_theme(alt.layer(chart, labels), height=260), width="stretch")

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
        on_click=log_dashboard_event,
        args=(
            "REPORT_EXPORTED",
            "report",
            stem,
            None,
            {
                "file_name": file_name,
                "format": "csv",
                "row_count": len(export_df),
                "run_id": run_id,
            },
        ),
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
        if not can_export_current_reports():
            export_panel.info("Your current role can view reports but cannot export them.")
            return

        selected_run_id = context.get("selected_run_id")
        timestamp = context.get("export_timestamp", datetime.now().strftime("%Y%m%d_%H%M%S"))

        try:
            executive_excel = export_run_to_excel(selected_run_id)
            excel_file_name = build_export_filename(
                "executive_report",
                selected_run_id,
                "xlsx",
                timestamp,
            )
            export_panel.download_button(
                label="Download Excel Report",
                data=executive_excel,
                file_name=excel_file_name,
                mime=(
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                ),
                key="download_executive_excel_report",
                on_click=log_dashboard_event,
                args=(
                    "REPORT_EXPORTED",
                    "report",
                    "executive_excel_report",
                    None,
                    {
                        "file_name": excel_file_name,
                        "format": "xlsx",
                        "run_id": selected_run_id,
                    },
                ),
            )
        except Exception:
            logger.exception("Could not build executive Excel report.")
            export_panel.info("Excel executive report is unavailable right now. Please check logs/app.log.")

        try:
            executive_pdf = export_run_to_pdf(selected_run_id)
            pdf_file_name = build_export_filename(
                "executive_summary",
                selected_run_id,
                "pdf",
                timestamp,
            )
            export_panel.download_button(
                label="Download PDF Executive Summary",
                data=executive_pdf,
                file_name=pdf_file_name,
                mime="application/pdf",
                key="download_executive_pdf_report",
                on_click=log_dashboard_event,
                args=(
                    "REPORT_EXPORTED",
                    "report",
                    "executive_pdf_summary",
                    None,
                    {
                        "file_name": pdf_file_name,
                        "format": "pdf",
                        "run_id": selected_run_id,
                    },
                ),
            )
        except ImportError as exc:
            export_panel.info(str(exc))
        except Exception:
            logger.exception("Could not build executive PDF report.")
            export_panel.info("PDF executive summary is unavailable right now. Please check logs/app.log.")

        export_panel.divider()
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
            on_click=log_dashboard_event,
            args=(
                "REPORT_EXPORTED",
                "report",
                "excel_report",
                None,
                {
                    "file_name": file_name,
                    "format": "xlsx",
                    "run_id": context.get("selected_run_id", "all"),
                },
            ),
        )


def resolve_alert(alert_id, assigned_to="", resolution_notes=""):
    """Mark a data quality alert as resolved in PostgreSQL."""

    query = text(
        """
        UPDATE data_quality_alerts
        SET
            is_resolved = TRUE,
            assigned_to = COALESCE(NULLIF(:assigned_to, ''), assigned_to),
            resolution_notes = COALESCE(NULLIF(:resolution_notes, ''), resolution_notes),
            resolved_at = CURRENT_TIMESTAMP
        WHERE id = :alert_id;
        """
    )

    try:
        engine = create_monitor_engine()
        with engine.begin() as connection:
            result = connection.execute(
                query,
                {
                    "alert_id": int(alert_id),
                    "assigned_to": assigned_to,
                    "resolution_notes": resolution_notes,
                },
            )
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
        "owner_team",
        "owner_email",
        "assigned_to",
        "message",
        "resolution_notes",
        "created_at",
    ]
    show_dataframe(open_alerts, columns=display_columns)

    st.markdown("#### Resolve Open Alerts")

    for _, alert in open_alerts.iterrows():
        alert_id = int(alert["id"])
        alert_type = alert.get("alert_type", "Unknown alert")
        severity = alert.get("severity", "UNKNOWN")
        message = alert.get("message", "")
        owner_team = alert.get("owner_team", "Unassigned")
        owner_email = alert.get("owner_email", "")
        current_assignee = alert.get("assigned_to", "")
        current_notes = alert.get("resolution_notes", "")

        with st.expander(f"Alert #{alert_id} | {severity} | {alert_type}"):
            st.markdown(
                f"{severity_badge(severity)} {alert_status_badge(False)}",
                unsafe_allow_html=True,
            )
            st.write(message)
            st.caption(f"Owner: {owner_team} | {owner_email or 'No owner email'}")

            if not can_resolve_alerts():
                st.caption("Your current role can view this alert but cannot resolve it.")
                continue

            with st.form(f"resolve_alert_form_{alert_id}"):
                assigned_to = st.text_input(
                    "Assigned To",
                    value=form_text_value(current_assignee),
                )
                resolution_notes = st.text_area(
                    "Resolution Notes",
                    value=form_text_value(current_notes),
                    height=100,
                )
                confirmed = True
                if str(severity).upper() == "CRITICAL":
                    confirmed = st.checkbox(
                        "I confirm this critical alert is ready to resolve.",
                        key=f"confirm_critical_{alert_id}",
                    )
                submitted = st.form_submit_button("Save and mark as resolved")

                if submitted:
                    if not confirmed:
                        st.warning("Confirm critical alert resolution before saving.")
                        return
                    if resolve_alert(alert_id, assigned_to, resolution_notes):
                        log_dashboard_event(
                            "ALERT_RESOLVED",
                            entity_type="alert",
                            entity_id=alert_id,
                            old_value=alert.to_dict(),
                            new_value={
                                "is_resolved": True,
                                "assigned_to": assigned_to,
                                "resolution_notes": resolution_notes,
                            },
                        )
                        st.success(f"Alert #{alert_id} marked as resolved.")
                        st.rerun()


def render_overview(context):
    section_header(
        "Executive Summary",
        "A management view of quality score, SLA health, critical issues, and open alerts.",
    )
    render_run_checks_action("overview")
    render_metrics(
        context["latest_run"],
        context["latest_alerts_df"],
        context.get("latest_sla_df"),
    )

    st.caption(
        "Quality score summarizes passing checks. Alerts identify operational follow-up. SLA status tracks dataset-level commitments."
    )

    section_header("Quality Trends", "Track how monitoring health changes across runs.")
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        render_quality_score_trend(context["runs_df"], context["alerts_df"])

    with chart_col2:
        render_failed_by_dataset(context["filtered_results"])

    section_header("Operational Focus", "Critical issues and open alerts requiring review.")
    focus_col1, focus_col2 = st.columns(2)

    with focus_col1:
        critical_df = rows_matching(context["filtered_results"], "severity", "CRITICAL")
        show_dataframe(
            critical_df,
            columns=[
                "dataset_name",
                "check_type",
                "column_name",
                "status",
                "severity",
                "failed_rows",
                "failure_rate",
            ],
            empty_message="No critical issues for this selection.",
        )

    with focus_col2:
        show_dataframe(
            filter_unresolved_alerts(context["latest_alerts_df"]),
            columns=[
                "alert_type",
                "severity",
                "owner_team",
                "assigned_to",
                "message",
                "is_resolved",
                "created_at",
            ],
            empty_message="No open alerts for the latest run.",
        )

    section_header("Failure Mix", "Failed checks grouped by check type and severity.")
    mix_col1, mix_col2 = st.columns(2)
    with mix_col1:
        render_failed_by_check_type(context["filtered_results"])
    with mix_col2:
        render_issues_by_severity(context["filtered_results"])


def render_run_checks_action(location_key):
    """Render a permission-aware dashboard action to trigger checks."""

    flash_key = "dashboard_run_checks_flash"
    if flash_key in st.session_state:
        flash = st.session_state.pop(flash_key)
        if flash.get("success"):
            st.success(flash.get("message", "Data quality checks completed."))
        else:
            st.error(flash.get("message", "Data quality checks failed."))
        if flash.get("stdout"):
            with st.expander("Command output summary"):
                st.code(flash["stdout"])
        if flash.get("stderr"):
            with st.expander("Error output"):
                st.code(flash["stderr"])

    if not can_run_dashboard_checks():
        st.caption("Your current role can view monitoring runs but cannot trigger checks.")
        return

    st.warning("This will execute data quality checks and may take some time.")
    confirm = st.checkbox(
        "I understand and want to run checks now.",
        key=f"confirm_run_checks_{location_key}",
    )

    if st.button(
        "Run Checks Now",
        key=f"run_checks_now_{location_key}",
        disabled=not confirm,
        type="primary",
    ):
        log_dashboard_event(
            "CHECKS_TRIGGERED_FROM_DASHBOARD",
            entity_type="monitoring_run",
            entity_id="manual_dashboard_trigger",
        )
        with st.spinner("Running data quality checks..."):
            try:
                result = run_checks_subprocess(PROJECT_ROOT, timeout_seconds=600)
            except subprocess.TimeoutExpired:
                logger.exception("Dashboard-triggered checks timed out.")
                st.session_state[flash_key] = {
                    "success": False,
                    "message": "Data quality checks timed out. Check logs/app.log.",
                    "stdout": "",
                    "stderr": "",
                }
            except Exception as exc:
                logger.exception("Dashboard-triggered checks failed to start.")
                st.session_state[flash_key] = {
                    "success": False,
                    "message": f"Could not start checks: {exc}",
                    "stdout": "",
                    "stderr": "",
                }
            else:
                st.session_state[flash_key] = {
                    "success": result["success"],
                    "message": (
                        "Data quality checks completed. Dashboard data has been refreshed."
                        if result["success"]
                        else "Data quality checks did not complete successfully."
                    ),
                    "stdout": result.get("stdout", ""),
                    "stderr": result.get("stderr", ""),
                }
            st.rerun()


def render_check_results(context):
    section_header(
        "Check Results",
        "Review validation results by status, severity, dataset, and check type.",
    )
    if not context["filtered_results"].empty:
        status_counts = (
            context["filtered_results"].get("status", pd.Series(dtype=str))
            .fillna("UNKNOWN")
            .astype(str)
            .str.upper()
            .value_counts()
        )
        severity_counts = (
            context["filtered_results"].get("severity", pd.Series(dtype=str))
            .fillna("UNKNOWN")
            .astype(str)
            .str.upper()
            .value_counts()
        )
        status_html = " ".join(
            f"{status_badge(status)} <span class='muted-text'>{count}</span>"
            for status, count in status_counts.items()
        )
        severity_html = " ".join(
            f"{severity_badge(severity)} <span class='muted-text'>{count}</span>"
            for severity, count in severity_counts.items()
        )
        st.markdown(f"{status_html}<br>{severity_html}", unsafe_allow_html=True)

    tabs = st.tabs(["All Results", "Failed", "Critical", "Anomaly & Drift", "Schema Drift"])

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

    with tabs[4]:
        if "check_type" in context["filtered_results"].columns:
            schema_results = context["filtered_results"][
                context["filtered_results"]["check_type"] == "schema_drift_check"
            ]
        else:
            schema_results = context["filtered_results"].iloc[0:0].copy()

        show_dataframe(
            schema_results,
            columns=[
                "dataset_name",
                "check_type",
                "rule",
                "total_rows",
                "failed_rows",
                "failure_rate",
                "status",
                "severity",
                "run_time",
            ],
            empty_message="No schema drift checks found for this selection.",
        )

        schema_summary = build_schema_drift_summary(context["filtered_details"])
        st.subheader("Schema Changes")
        show_dataframe(
            schema_summary,
            columns=[
                "dataset_name",
                "column_name",
                "change_type",
                "previous_data_type",
                "current_data_type",
                "previous_nullable",
                "current_nullable",
                "previous_position",
                "current_position",
                "reason",
            ],
            empty_message="No schema changes found for this selection.",
        )


def render_issue_details(context):
    section_header(
        "Issue Details",
        "Investigate failed-row examples and root-cause context.",
    )
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
    section_header(
        "Alert Management",
        "Triage open alerts, assign owners, capture resolution notes, and review ownership.",
    )

    selected_alerts = context["filtered_alerts"].copy()
    open_alerts = filter_unresolved_alerts(selected_alerts)
    resolved_alerts = filter_resolved_alerts(selected_alerts)
    critical_alerts = rows_matching(selected_alerts, "severity", "CRITICAL")
    escalated_alerts = rows_matching(selected_alerts, "escalation_status", "ESCALATED")

    metric_cols = st.columns(4)
    with metric_cols[0]:
        metric_card("Total Alerts", len(selected_alerts), "Current filters", "info")
    with metric_cols[1]:
        metric_card("Open Alerts", len(open_alerts), "Unresolved items", _count_status(len(open_alerts)))
    with metric_cols[2]:
        metric_card("Critical Alerts", len(critical_alerts), "Highest severity", _count_status(len(critical_alerts)))
    with metric_cols[3]:
        metric_card("Resolved Alerts", len(resolved_alerts), "Closed items", "success")

    if context.get("selected_alert_severity") != "All":
        st.caption(f"Alert severity filter: {context['selected_alert_severity']}")
    if context.get("selected_alert_owner") != "All":
        st.caption(f"Owner filter: {context['selected_alert_owner']}")
    if context.get("selected_alert_status") != "All":
        st.caption(f"Resolved status filter: {context['selected_alert_status']}")

    if selected_alerts.empty:
        empty_state("No alerts found", "No alerts match the selected filters.")
        return

    st.markdown(
        f"{alert_status_badge(False)} <span class='muted-text'>{len(open_alerts)}</span> "
        f"{alert_status_badge(True)} <span class='muted-text'>{len(resolved_alerts)}</span>",
        unsafe_allow_html=True,
    )

    tabs = st.tabs(["Open Alerts", "Escalated Alerts", "Resolved Alerts", "All Alerts", "Edit Alert", "Ownership"])

    with tabs[0]:
        render_alert_resolution_cards(open_alerts)

    with tabs[1]:
        show_dataframe(
            escalated_alerts,
            columns=[
                "id",
                "run_id",
                "alert_type",
                "severity",
                "owner_team",
                "assigned_to",
                "message",
                "sla_due_at",
                "escalation_status",
                "escalation_level",
                "escalated_at",
                "created_at",
            ],
            empty_message="No escalated alerts for this selection.",
        )

    with tabs[2]:
        show_dataframe(
            resolved_alerts,
            columns=[
                "id",
                "run_id",
                "alert_type",
                "severity",
                "owner_team",
                "owner_email",
                "assigned_to",
                "message",
                "resolution_notes",
                "resolved_at",
                "created_at",
            ],
            empty_message="No resolved alerts for this selection.",
        )

    with tabs[3]:
        show_dataframe(
            selected_alerts,
            columns=[
                "id",
                "run_id",
                "alert_type",
                "severity",
                "owner_team",
                "owner_email",
                "assigned_to",
                "message",
                "is_resolved",
                "resolution_notes",
                "sla_due_at",
                "escalation_status",
                "escalation_level",
                "escalated_at",
                "resolved_at",
                "created_at",
            ],
            empty_message="No alerts found for the selected run.",
        )

    with tabs[4]:
        section_header("Edit Alert", "Update assignment, ownership, severity, or resolution notes.")

        if "id" not in selected_alerts.columns:
            warning_state("Alert IDs missing", "Cannot edit alerts because the id column is missing.")
            return

        if not can_edit_alerts():
            warning_state("View-only access", "Your current role can view alerts but cannot edit them.")
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

        old_alert_value = alert_row.to_dict()

        with st.form("edit_alert_form"):
            alert_type = st.text_input(
                "Alert Type",
                value=str(alert_row.get("alert_type", "")),
            )

            severity_col, owner_col = st.columns(2)
            with severity_col:
                severity = st.selectbox(
                    "Severity",
                    options=severity_options,
                    index=severity_options.index(current_severity),
                )
            with owner_col:
                owner_team = st.text_input(
                    "Owner Team",
                    value=form_text_value(alert_row.get("owner_team", "")),
                )

            message = st.text_area(
                "Message",
                value=str(alert_row.get("message", "")),
                height=150,
            )

            owner_email_col, assigned_col = st.columns(2)
            with owner_email_col:
                owner_email = st.text_input(
                    "Owner Email",
                    value=form_text_value(alert_row.get("owner_email", "")),
                )
            with assigned_col:
                assigned_to = st.text_input(
                    "Assigned To",
                    value=form_text_value(alert_row.get("assigned_to", "")),
                )

            resolution_notes = st.text_area(
                "Resolution Notes",
                value=form_text_value(alert_row.get("resolution_notes", "")),
                height=130,
            )

            is_resolved = st.checkbox(
                "Resolved",
                value=bool(current_resolved),
            )

            if is_resolved and str(severity).upper() == "CRITICAL":
                st.warning("Critical alerts should only be resolved after owner review is complete.")

            submitted = st.form_submit_button("Save Alert Changes")

            if submitted:
                if update_alert(
                    alert_id=selected_alert_id,
                    alert_type=alert_type,
                    severity=severity,
                    message=message,
                    is_resolved=is_resolved,
                    owner_team=owner_team,
                    owner_email=owner_email,
                    assigned_to=assigned_to,
                    resolution_notes=resolution_notes,
                ):
                    log_dashboard_event(
                        "ALERT_EDITED",
                        entity_type="alert",
                        entity_id=selected_alert_id,
                        old_value=old_alert_value,
                        new_value={
                            "alert_type": alert_type,
                            "severity": severity,
                            "message": message,
                            "owner_team": owner_team,
                            "owner_email": owner_email,
                            "assigned_to": assigned_to,
                            "resolution_notes": resolution_notes,
                            "is_resolved": is_resolved,
                        },
                    )
                    st.success(f"Alert {selected_alert_id} updated successfully.")
                    st.rerun()

    with tabs[5]:
        section_header("Ownership", "Alert workload by owner team and assignee.")
        if selected_alerts.empty:
            empty_state("No ownership data", "No alerts are available for this selection.")
        else:
            ownership_df = selected_alerts.copy()
            if "owner_team" not in ownership_df.columns:
                ownership_df["owner_team"] = "Unassigned"
            if "assigned_to" not in ownership_df.columns:
                ownership_df["assigned_to"] = "Unassigned"
            ownership_summary = (
                ownership_df
                .fillna({"owner_team": "Unassigned", "assigned_to": "Unassigned"})
                .groupby(["owner_team", "assigned_to"])
                .size()
                .reset_index(name="alert_count")
                .sort_values("alert_count", ascending=False)
            )
            show_dataframe(
                ownership_summary,
                empty_message="No ownership summary available.",
            )


def render_data_profiling(context):
    section_header(
        "Data Profiling",
        "Column-level shape, null, uniqueness, and numeric profile information.",
    )
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


def render_row_volume(context):
    section_header(
        "Row Volume",
        "Monitor sudden row count drops and spikes across ingestion runs.",
    )

    volume_df = context.get("volume_df", pd.DataFrame()).copy()
    selected_volume = context.get("filtered_volume", pd.DataFrame()).copy()

    if volume_df.empty:
        empty_state(
            "No row volume history",
            "Run monitoring checks to start building row volume baselines.",
        )
        return

    selected_dataset = context.get("selected_dataset", "All")
    history_df = filter_by_value(volume_df, "dataset_name", selected_dataset)

    metric_cols = st.columns(4)
    with metric_cols[0]:
        metric_card("History Rows", len(history_df), "Current dataset filter", "info")
    with metric_cols[1]:
        fail_count = (
            int((history_df["status"].fillna("").astype(str).str.upper() == "FAIL").sum())
            if "status" in history_df.columns
            else 0
        )
        metric_card("Anomalies", fail_count, "Historical failures", _count_status(fail_count))
    with metric_cols[2]:
        latest_count = (
            history_df["row_count"].iloc[0]
            if "row_count" in history_df.columns and not history_df.empty
            else "N/A"
        )
        metric_card("Latest Row Count", latest_count, "Most recent selected row", "neutral")
    with metric_cols[3]:
        latest_change = (
            history_df["percent_change"].iloc[0]
            if "percent_change" in history_df.columns and not history_df.empty
            else None
        )
        metric_card(
            "Latest Change",
            "N/A" if pd.isna(latest_change) else f"{float(latest_change):.1f}%",
            "Vs baseline",
            "neutral",
        )

    chart_df = history_df.copy()
    if not chart_df.empty and {"run_id", "dataset_name", "row_count"}.issubset(chart_df.columns):
        chart_df = chart_df.sort_values(["dataset_name", "run_id"])
        chart_df["run_label"] = chart_df["run_id"].astype(str)
        chart = alt.Chart(chart_df).mark_line(
            strokeWidth=3,
            point=alt.OverlayMarkDef(size=70, filled=True),
        ).encode(
            x=alt.X(
                "run_label:N",
                title="Run ID",
                sort=list(chart_df["run_label"].drop_duplicates()),
                axis=alt.Axis(labelAngle=0),
            ),
            y=alt.Y("row_count:Q", title="Row Count"),
            color=alt.Color("dataset_name:N", title="Dataset"),
            tooltip=[
                alt.Tooltip("run_id:O", title="Run ID"),
                alt.Tooltip("dataset_name:N", title="Dataset"),
                alt.Tooltip("row_count:Q", title="Row Count", format=",.0f"),
                alt.Tooltip("baseline_row_count:Q", title="Baseline", format=",.1f"),
                alt.Tooltip("percent_change:Q", title="Change %", format=".1f"),
                alt.Tooltip("status:N", title="Status"),
                alt.Tooltip("severity:N", title="Severity"),
            ],
        )
        st.altair_chart(apply_enterprise_chart_theme(chart, height=340), width="stretch")
    else:
        empty_state("No chartable volume data", "Row volume history is missing run, dataset, or row-count columns.")

    st.subheader("Selected Run Volume Status")
    show_dataframe(
        selected_volume,
        columns=[
            "run_id",
            "dataset_name",
            "row_count",
            "baseline_row_count",
            "percent_change",
            "status",
            "severity",
            "created_at",
        ],
        empty_message="No row volume rows found for this selection.",
    )

    st.subheader("Historical Volume Anomalies")
    anomalies = history_df
    if "status" in anomalies.columns:
        anomalies = anomalies[anomalies["status"].fillna("").astype(str).str.upper() == "FAIL"]
    else:
        anomalies = anomalies.iloc[0:0].copy()
    show_dataframe(
        anomalies,
        columns=[
            "run_id",
            "dataset_name",
            "row_count",
            "baseline_row_count",
            "percent_change",
            "status",
            "severity",
            "created_at",
        ],
        empty_message="No row volume anomalies found for this dataset selection.",
    )


def render_rules_catalog(context):
    section_header(
        "Rules Catalog",
        "Browse active YAML rules without opening configuration files.",
    )

    rules_df = context.get("rules_catalog_df", pd.DataFrame()).copy()
    raw_rules = context.get("rules_catalog_raw", {})

    if rules_df.empty:
        empty_state(
            "No rules found",
            "Add rules to config/rules.yaml and refresh the dashboard.",
        )
        return

    metric_cols = st.columns(4)
    with metric_cols[0]:
        metric_card("Total Rules", len(rules_df), "Flattened active rows", "info")
    with metric_cols[1]:
        metric_card("Datasets", rules_df["dataset_name"].nunique(), "Including GLOBAL", "neutral")
    with metric_cols[2]:
        metric_card("Rule Types", rules_df["rule_type"].nunique(), "Configured checks", "neutral")
    with metric_cols[3]:
        disabled_count = (
            int((rules_df["enabled"].astype(str).str.lower() == "false").sum())
            if "enabled" in rules_df.columns
            else 0
        )
        metric_card("Disabled", disabled_count, "Explicitly disabled", _count_status(disabled_count))

    chart_cols = st.columns(2)
    with chart_cols[0]:
        by_dataset = (
            rules_df.groupby("dataset_name")
            .size()
            .reset_index(name="rule_count")
            .sort_values("rule_count", ascending=False)
        )
        chart = alt.Chart(by_dataset).mark_bar(
            cornerRadiusTopRight=5,
            cornerRadiusBottomRight=5,
        ).encode(
            y=alt.Y("dataset_name:N", title=None, sort="-x"),
            x=alt.X("rule_count:Q", title="Rules", axis=alt.Axis(format="d")),
            color=alt.value(BRAND.primary_color),
            tooltip=[
                alt.Tooltip("dataset_name:N", title="Dataset"),
                alt.Tooltip("rule_count:Q", title="Rules"),
            ],
        )
        st.altair_chart(apply_enterprise_chart_theme(chart, height=280), width="stretch")

    with chart_cols[1]:
        by_type = (
            rules_df.groupby("rule_type")
            .size()
            .reset_index(name="rule_count")
            .sort_values("rule_count", ascending=False)
            .head(12)
        )
        chart = alt.Chart(by_type).mark_bar(
            cornerRadiusTopRight=5,
            cornerRadiusBottomRight=5,
        ).encode(
            y=alt.Y("rule_type:N", title=None, sort="-x"),
            x=alt.X("rule_count:Q", title="Rules", axis=alt.Axis(format="d")),
            color=alt.value(BRAND.accent_color),
            tooltip=[
                alt.Tooltip("rule_type:N", title="Rule Type"),
                alt.Tooltip("rule_count:Q", title="Rules"),
            ],
        )
        st.altair_chart(apply_enterprise_chart_theme(chart, height=280), width="stretch")

    filter_cols = st.columns(4)
    with filter_cols[0]:
        selected_dataset = st.selectbox(
            "Catalog Dataset",
            options=["All"] + unique_options(rules_df, "dataset_name"),
        )
    with filter_cols[1]:
        selected_rule_type = st.selectbox(
            "Rule Type",
            options=["All"] + unique_options(rules_df, "rule_type"),
        )
    with filter_cols[2]:
        selected_column = st.selectbox(
            "Column",
            options=["All"] + unique_options(rules_df, "column_name"),
        )
    with filter_cols[3]:
        search_text = st.text_input("Search Rules", value="")

    filtered_rules = filter_by_value(rules_df, "dataset_name", selected_dataset)
    filtered_rules = filter_by_value(filtered_rules, "rule_type", selected_rule_type)
    filtered_rules = filter_by_value(filtered_rules, "column_name", selected_column)

    if search_text.strip():
        search_lower = search_text.strip().lower()
        search_frame = filtered_rules.fillna("").astype(str)
        filtered_rules = filtered_rules[
            search_frame.apply(
                lambda row: row.str.lower().str.contains(search_lower, regex=False).any(),
                axis=1,
            )
        ]

    export_name = build_export_filename(
        "rules_catalog",
        "all",
        "csv",
        context.get("export_timestamp", datetime.now().strftime("%Y%m%d_%H%M%S")),
    )
    st.download_button(
        label="Download rules catalog CSV",
        data=dataframe_to_csv_bytes(filtered_rules),
        file_name=export_name,
        mime="text/csv",
        key="download_rules_catalog_csv",
        disabled=filtered_rules.empty,
        on_click=log_dashboard_event,
        args=(
            "REPORT_EXPORTED",
            "report",
            "rules_catalog",
            None,
            {
                "file_name": export_name,
                "format": "csv",
                "row_count": len(filtered_rules),
            },
        ),
    )

    show_dataframe(
        filtered_rules,
        columns=[
            "dataset_name",
            "rule_type",
            "column_name",
            "severity",
            "enabled",
            "rule_config",
        ],
        empty_message="No rules match the selected filters.",
        height=520,
    )

    st.info("Rule editing and approval workflow is a Pro/Enterprise roadmap feature.")

    with st.expander("View raw YAML", expanded=False):
        st.code(rules_to_yaml(raw_rules), language="yaml")


def render_data_lineage(context):
    section_header(
        "Data Lineage",
        "Understand upstream and downstream table dependencies.",
    )

    edges_df = context["lineage_edges_df"]

    if edges_df.empty:
        empty_state(
            "No lineage configuration found",
            "Add relationships to config/lineage.yaml to visualize dependencies.",
        )
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
    section_header(
        "SLA Tracking",
        "Track dataset-level service commitments and historical violations.",
    )

    selected_sla = context["filtered_sla"].copy()
    historical_sla = filter_by_value(
        context["sla_df"],
        "dataset_name",
        context.get("selected_dataset", "All"),
    )
    selected_violations = filter_sla_violations(selected_sla)
    historical_violations = filter_sla_violations(historical_sla)

    if selected_sla.empty:
        empty_state("No SLA results", "No SLA results found for this selection.")
    else:
        status_values = selected_sla["sla_status"].fillna("").astype(str).str.upper()
        sla_counts = status_values.value_counts()
        sla_html = " ".join(
            f"{sla_badge(status)} <span class='muted-text'>{count}</span>"
            for status, count in sla_counts.items()
        )
        st.markdown(sla_html, unsafe_allow_html=True)
        quality_values = pd.to_numeric(
            selected_sla.get("actual_quality_score", pd.Series(dtype=float)),
            errors="coerce",
        )
        avg_quality_score = quality_values.mean()
        metric_cols = st.columns(4)
        with metric_cols[0]:
            metric_card("Datasets Evaluated", len(selected_sla), "Current selection", "info")
        with metric_cols[1]:
            metric_card("SLA Met", int((status_values == "PASS").sum()), "Passing datasets", "success")
        with metric_cols[2]:
            metric_card("SLA Violations", len(selected_violations), "Needs attention", _count_status(len(selected_violations)))
        with metric_cols[3]:
            metric_card(
                "Avg Quality Score",
                "N/A" if pd.isna(avg_quality_score) else f"{avg_quality_score:.1f}%",
                "Across selected SLA rows",
                "neutral",
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
        empty_state("No SLA trend data", "Run multiple monitoring cycles to build an SLA trend.")
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
        )

        st.altair_chart(apply_enterprise_chart_theme(chart, height=320), width="stretch")

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
    section_header("Run History", "Historical monitoring executions and quality scores.")
    show_dataframe(
        context["runs_df"],
        empty_message="No run history found.",
    )


def render_audit_logs(context):
    """Render enterprise audit logs for admin users."""

    section_header(
        "Audit Logs",
        "Review operational actions across dashboard and API workflows.",
    )

    if current_user_role() != "admin":
        warning_state("Admin access required", "Audit Logs are visible only to admin users.")
        return

    audit_df = context.get("audit_logs_df", pd.DataFrame()).copy()

    if audit_df.empty:
        empty_state("No audit events found", "Operational audit events will appear here after user or API actions.")
        return

    filter_cols = st.columns(3)
    with filter_cols[0]:
        selected_event_type = st.selectbox(
            "Event Type",
            options=["All"] + unique_options(audit_df, "event_type"),
        )
    with filter_cols[1]:
        selected_username = st.selectbox(
            "Username",
            options=["All"] + unique_options(audit_df, "username"),
        )
    with filter_cols[2]:
        selected_entity_type = st.selectbox(
            "Entity Type",
            options=["All"] + unique_options(audit_df, "entity_type"),
        )

    filtered_audit = filter_by_value(audit_df, "event_type", selected_event_type)
    filtered_audit = filter_by_value(filtered_audit, "username", selected_username)
    filtered_audit = filter_by_value(filtered_audit, "entity_type", selected_entity_type)

    if "created_at" in filtered_audit.columns:
        created_values = pd.to_datetime(filtered_audit["created_at"], errors="coerce")
        valid_dates = created_values.dropna()
        if not valid_dates.empty:
            min_date = valid_dates.min().date()
            max_date = valid_dates.max().date()
            selected_range = st.date_input(
                "Date Range",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
            )
            if isinstance(selected_range, tuple) and len(selected_range) == 2:
                start_date, end_date = selected_range
                date_mask = (
                    (created_values.dt.date >= start_date)
                    & (created_values.dt.date <= end_date)
                )
                filtered_audit = filtered_audit[date_mask]

    metric_cols = st.columns(4)
    with metric_cols[0]:
        metric_card("Audit Events", len(filtered_audit), "Current filters", "info")
    with metric_cols[1]:
        metric_card("Event Types", filtered_audit.get("event_type", pd.Series(dtype=str)).nunique(), "Distinct actions", "neutral")
    with metric_cols[2]:
        metric_card("Users", filtered_audit.get("username", pd.Series(dtype=str)).nunique(), "Actors", "neutral")
    with metric_cols[3]:
        latest_event = (
            filtered_audit["created_at"].iloc[0]
            if "created_at" in filtered_audit.columns and not filtered_audit.empty
            else "N/A"
        )
        metric_card("Latest Event", latest_event, "Most recent", "info")

    show_dataframe(
        filtered_audit,
        columns=[
            "id",
            "event_type",
            "username",
            "role",
            "entity_type",
            "entity_id",
            "ip_address",
            "created_at",
            "old_value",
            "new_value",
        ],
        empty_message="No audit logs match the selected filters.",
        height=520,
    )


def render_setup_wizard(context):
    """Render setup guidance for first-time users."""

    section_header(
        "Setup Wizard",
        "Validate configuration health and follow the recommended setup commands.",
    )

    if st.button("Refresh setup checks", key="refresh_setup_checks"):
        log_dashboard_event(
            "CONFIG_VALIDATED",
            entity_type="configuration",
            entity_id="dashboard_setup_wizard",
        )
        st.rerun()

    try:
        validation_results = validate_config()
    except Exception:
        logger.exception("Setup Wizard validation failed.")
        validation_results = [{
            "name": "setup validation",
            "status": "FAIL",
            "message": "Could not run configuration validation.",
            "recommended_fix": "python cli.py validate-config",
        }]

    status_counts = pd.Series(
        [result["status"] for result in validation_results],
        dtype=str,
    ).value_counts()

    command_cols = st.columns(4)
    with command_cols[0]:
        metric_card("PASS", int(status_counts.get("PASS", 0)), "Healthy checks", "success")
    with command_cols[1]:
        metric_card("WARNING", int(status_counts.get("WARNING", 0)), "Needs attention", "warning")
    with command_cols[2]:
        metric_card("FAIL", int(status_counts.get("FAIL", 0)), "Blocking checks", _count_status(status_counts.get("FAIL", 0)))
    with command_cols[3]:
        metric_card("Version", get_version(), "Current build", "info")

    st.markdown("#### Run Checks")
    render_run_checks_action("setup_wizard")

    st.markdown("#### Health Checklist")

    for result in validation_results:
        st.markdown(
            f"""
            <div class="enterprise-card" style="padding:0.9rem 1rem;margin-bottom:0.55rem;">
                <div style="display:flex;align-items:center;justify-content:space-between;gap:1rem;">
                    <div>
                        <div style="font-weight:800;">{escape(result["name"])}</div>
                        <div class="muted-text" style="font-size:0.86rem;margin-top:0.2rem;">
                            {escape(result["message"])}
                        </div>
                    </div>
                    <div>{status_badge(result["status"])}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if result["status"] != "PASS" and result.get("recommended_fix"):
            st.code(result["recommended_fix"], language="powershell")

    st.markdown("#### Common Commands")

    show_dataframe(
        pd.DataFrame([
            {
                "Area": "Configuration",
                "Action": "Copy .env.example to .env and update database credentials.",
            },
            {
                "Area": "Validation",
                "Action": "Run python cli.py validate-config.",
            },
            {
                "Area": "Database",
                "Action": "Run python cli.py init-db.",
            },
            {
                "Area": "Demo Data",
                "Action": "Run python cli.py seed-demo.",
            },
            {
                "Area": "Checks",
                "Action": "Run python cli.py run-checks.",
            },
            {
                "Area": "Dashboard",
                "Action": "Run python -m streamlit run dashboard/app.py.",
            },
        ]),
        empty_message="No setup guidance available.",
    )


def render_sidebar_navigation():
    """Render grouped enterprise navigation and return selected page."""

    navigation_groups = {
        "Monitoring": [
            ("Overview", "Overview"),
            ("Check Results", "Check Results"),
            ("Issue Details", "Issue Details"),
            ("Alerts", "Alerts"),
        ],
        "Governance": [
            ("Data Profiling", "Data Profiling"),
            ("Row Volume", "Row Volume"),
            ("Rules Catalog", "Rules Catalog"),
            ("SLA Tracking", "SLA Tracking"),
            ("Data Lineage", "Data Lineage"),
        ],
        "Admin": [
            ("Setup Wizard", "Setup Wizard"),
            ("Run History", "Run History"),
        ],
    }
    if current_user_role() == "admin":
        navigation_groups["Admin"].append(("Audit Logs", "Audit Logs"))

    icons = {
        "Overview": "▣",
        "Check Results": "▥",
        "Issue Details": "◬",
        "Alerts": "◆",
        "Data Profiling": "▤",
        "SLA Tracking": "◴",
        "Data Lineage": "⧉",
        "Reports": "▦",
        "Settings": "⚙",
        "Setup Wizards": "◫",
        "Governance": "◫"
    }
    icons["Audit Logs"] = "A"
    icons["Row Volume"] = "V"
    icons["Rules Catalog"] = "R"

    query_page = st.query_params.get("page")
    all_pages = {
        page_value
        for pages in navigation_groups.values()
        for _, page_value in pages
    }

    if query_page in all_pages:
        st.session_state["dashboard_page"] = query_page

    if "dashboard_page" not in st.session_state:
        st.session_state["dashboard_page"] = "Overview"

    st.sidebar.markdown('<div class="nav-group-label">Navigation</div>', unsafe_allow_html=True)

    for group_name, pages in navigation_groups.items():
        st.sidebar.markdown(
            '<div class="sidebar-section-label">Navigation</div>',
            unsafe_allow_html=True,
        )

        for page_name, page_value in pages:
            is_active = st.session_state["dashboard_page"] == page_value
            label = f"{icons.get(page_name, '▣')}  {page_name}"

            if st.sidebar.button(
                    label,
                    key=f"nav_{page_value.replace(' ', '_').lower()}",
                    width="stretch",
                    type="primary" if is_active else "secondary",
            ):
                st.session_state["dashboard_page"] = page_value
                st.query_params["page"] = page_value
                st.rerun()
    inject_sidebar_nav_css()
    return st.session_state["dashboard_page"]


def build_sidebar_filters(
    runs_df,
    results_df,
    details_df,
    alerts_df,
    profiles_df,
    volume_df,
    sla_df,
    lineage_edges_df,
):
    """Build sidebar navigation and filters."""

    render_sidebar_branding()
    page = render_sidebar_navigation()

    authenticated_user = st.session_state.get("dashboard_authenticated_user")
    if authenticated_user:
        role = current_user_role()
        st.sidebar.markdown(
            f"""
            <div class="sidebar-user-card">
                <div class="sidebar-user-name">{escape(str(authenticated_user))}</div>
                <div class="sidebar-user-role">Role: {escape(str(role))}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.sidebar.button("Logout", key="dashboard_logout", width="stretch"):
            log_dashboard_event(
                "USER_LOGOUT",
                entity_type="dashboard_session",
                entity_id=authenticated_user,
            )
            clear_dashboard_login_state(st.session_state)
            st.rerun()

    st.sidebar.divider()
    st.sidebar.markdown('<div class="nav-group-label">Filters</div>', unsafe_allow_html=True)

    run_ids = runs_df["run_id"].tolist()
    selected_run_id = st.sidebar.selectbox("Run ID", options=run_ids, index=0)

    run_results = filter_by_value(results_df, "run_id", selected_run_id)
    run_details = filter_by_value(details_df, "run_id", selected_run_id)
    run_alerts = filter_by_value(alerts_df, "run_id", selected_run_id)
    run_profiles = filter_by_value(profiles_df, "run_id", selected_run_id)
    run_volume = filter_by_value(volume_df, "run_id", selected_run_id)
    run_sla = filter_by_value(sla_df, "run_id", selected_run_id)

    dataset_options = sorted(set(
        unique_options(run_results, "dataset_name")
        + unique_options(run_details, "dataset_name")
        + unique_options(run_profiles, "dataset_name")
        + unique_options(run_volume, "dataset_name")
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
    dataset_volume = filter_by_value(run_volume, "dataset_name", selected_dataset)
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

    selected_alert_owner = st.sidebar.selectbox(
        "Alert Owner Team",
        options=["All"] + unique_options(filtered_alerts, "owner_team"),
    )
    filtered_alerts = filter_by_value(filtered_alerts, "owner_team", selected_alert_owner)

    selected_alert_assignee = st.sidebar.selectbox(
        "Assigned To",
        options=["All"] + unique_options(filtered_alerts, "assigned_to"),
    )
    filtered_alerts = filter_by_value(filtered_alerts, "assigned_to", selected_alert_assignee)

    selected_alert_status = st.sidebar.selectbox(
        "Resolved Status",
        options=["All", "Open", "Resolved"],
    )

    if selected_alert_status == "Open":
        filtered_alerts = filter_unresolved_alerts(filtered_alerts)
    elif selected_alert_status == "Resolved":
        filtered_alerts = filter_resolved_alerts(filtered_alerts)

    st.sidebar.divider()
    st.sidebar.caption(f"Version: {get_version()}")

    return {
        "page": page,
        "selected_run_id": selected_run_id,
        "selected_dataset": selected_dataset,
        "selected_status": selected_status,
        "selected_severity": selected_severity,
        "selected_alert_severity": selected_alert_severity,
        "selected_alert_owner": selected_alert_owner,
        "selected_alert_assignee": selected_alert_assignee,
        "selected_alert_status": selected_alert_status,
        "filtered_results": filtered_results,
        "filtered_details": filtered_details,
        "filtered_alerts": filtered_alerts,
        "filtered_profiles": dataset_profiles,
        "filtered_volume": dataset_volume,
        "filtered_sla": dataset_sla,
    }
def inject_sidebar_nav_css() -> None:
    st.markdown(
        """
        <style>
        /* Sidebar navigation buttons */
        section[data-testid="stSidebar"] div.stButton > button {
            width: 100%;
            justify-content: flex-start;
            text-align: left;
            border-radius: 12px;
            padding: 0.68rem 0.85rem;
            margin: 0.12rem 0 0.35rem 0;
            font-weight: 650;
            letter-spacing: 0.01em;
            border: 1px solid rgba(148, 163, 184, 0.22);
            background: rgba(15, 23, 42, 0.35);
            color: rgba(226, 232, 240, 0.86);
            box-shadow: none;
            transition: all 160ms ease;
        }

        section[data-testid="stSidebar"] div.stButton > button:hover {
            transform: translateX(2px);
            border-color: rgba(96, 165, 250, 0.55);
            background: rgba(30, 41, 59, 0.78);
            color: #ffffff;
        }

        /* Active navigation item */
        section[data-testid="stSidebar"] div.stButton > button[kind="primary"] {
            position: relative;
            border-left: 5px solid #38bdf8;
            border-top: 1px solid rgba(56, 189, 248, 0.70);
            border-right: 1px solid rgba(56, 189, 248, 0.40);
            border-bottom: 1px solid rgba(56, 189, 248, 0.40);
            background: linear-gradient(
                90deg,
                rgba(14, 165, 233, 0.34),
                rgba(30, 41, 59, 0.78)
            );
            color: #ffffff;
            font-weight: 800;
            box-shadow:
                inset 0 0 0 1px rgba(255, 255, 255, 0.05),
                0 8px 22px rgba(14, 165, 233, 0.18);
        }

        section[data-testid="stSidebar"] div.stButton > button[kind="primary"]::before {
            content: "●";
            color: #22c55e;
            font-size: 0.62rem;
            margin-right: 0.45rem;
            line-height: 1;
        }

        section[data-testid="stSidebar"] div.stButton > button[kind="primary"]:hover {
            transform: translateX(2px);
            background: linear-gradient(
                90deg,
                rgba(14, 165, 233, 0.44),
                rgba(30, 41, 59, 0.88)
            );
        }

        .sidebar-section-label {
            margin: 1.2rem 0 0.55rem 0;
            font-size: 0.72rem;
            font-weight: 800;
            letter-spacing: 0.11em;
            color: rgba(148, 163, 184, 0.86);
            text-transform: uppercase;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

def main():
    runs_df = load_quality_runs()
    results_df = load_quality_results()
    details_df = load_issue_details()
    alerts_df = load_alerts()
    profiles_df = load_profile_results()
    volume_df = load_volume_history()
    sla_df = load_sla_results()
    audit_logs_df = load_audit_logs()
    lineage_edges_df = load_lineage_edges()
    rules_catalog_raw, rules_catalog_df = load_dashboard_rules_catalog()

    if runs_df.empty or "run_id" not in runs_df.columns:
        render_app_header(status="SETUP", last_refresh=datetime.now())
        warning_state(
            "No data quality runs found",
            "Run checks to generate the first monitoring run, then refresh this dashboard.",
        )
        st.code("python cli.py run-checks", language="powershell")
        render_rules_catalog({
            "rules_catalog_raw": rules_catalog_raw,
            "rules_catalog_df": rules_catalog_df,
            "export_timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
        })
        render_data_lineage({
            "lineage_edges_df": lineage_edges_df,
            "filtered_results": pd.DataFrame(),
            "filtered_details": pd.DataFrame(),
            "selected_dataset": "All",
        })
        render_footer()
        return

    latest_run = runs_df.iloc[0]
    latest_run_id = int(latest_run["run_id"])
    latest_alerts_df = filter_by_value(alerts_df, "run_id", latest_run_id)
    latest_sla_df = filter_by_value(sla_df, "run_id", latest_run_id)

    render_app_header(
        status=latest_run.get("overall_status", "UNKNOWN"),
        last_refresh=datetime.now(),
    )

    filters = build_sidebar_filters(
        runs_df,
        results_df,
        details_df,
        alerts_df,
        profiles_df,
        volume_df,
        sla_df,
        lineage_edges_df,
    )
    context = {
        "runs_df": runs_df,
        "results_df": results_df,
        "details_df": details_df,
        "alerts_df": alerts_df,
        "profiles_df": profiles_df,
        "volume_df": volume_df,
        "sla_df": sla_df,
        "audit_logs_df": audit_logs_df,
        "lineage_edges_df": lineage_edges_df,
        "rules_catalog_raw": rules_catalog_raw,
        "rules_catalog_df": rules_catalog_df,
        "latest_run": latest_run,
        "latest_alerts_df": latest_alerts_df,
        "latest_sla_df": latest_sla_df,
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
        "Row Volume": render_row_volume,
        "Rules Catalog": render_rules_catalog,
        "Data Lineage": render_data_lineage,
        "SLA Tracking": render_sla_tracking,
        "Setup Wizard": render_setup_wizard,
        "Run History": render_run_history,
        "Audit Logs": render_audit_logs,
    }
    pages[filters["page"]](context)
    render_footer()


if __name__ == "__main__":
    main()
