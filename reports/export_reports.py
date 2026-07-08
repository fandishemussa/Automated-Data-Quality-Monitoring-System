"""Enterprise Excel and PDF report exports for monitoring runs."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import text

from data_sources.postgres_connector import create_monitor_engine
from lineage.lineage_service import get_all_lineage_edges
from utils.logger import get_logger


logger = get_logger(__name__)

REPORT_SHEETS = {
    "Executive Summary": "summary",
    "Check Results": "results",
    "Failed Checks": "failed_checks",
    "Issue Details": "issue_details",
    "Alerts": "alerts",
    "SLA Results": "sla_results",
    "Data Profiling": "profiles",
    "Lineage": "lineage",
}


def export_run_to_excel(run_id: int, output_path: str | Path | None = None) -> bytes | Path:
    """Export a monitoring run to a formatted Excel workbook.

    When `output_path` is omitted, workbook bytes are returned for dashboard
    download buttons. When supplied, the workbook is written and the path is
    returned.
    """

    report_data = load_run_report_data(run_id)
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for sheet_name, data_key in REPORT_SHEETS.items():
            df = report_data.get(data_key, pd.DataFrame())
            export_df = _safe_frame(df)
            if export_df.empty:
                export_df = pd.DataFrame({"message": ["No records for this run."]})
            export_df.to_excel(writer, sheet_name=sheet_name, index=False)
            _format_worksheet(writer.book[sheet_name])

    output.seek(0)
    data = output.getvalue()

    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        logger.info("Exported run %s Excel report to %s.", run_id, path)
        return path

    return data


def export_run_to_pdf(run_id: int, output_path: str | Path | None = None) -> bytes | Path:
    """Export a lightweight PDF executive summary for a run.

    Requires `reportlab`. If it is not installed, an ImportError is raised with
    a clear install instruction.
    """

    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as exc:
        raise ImportError(
            "PDF export requires reportlab. Install it with: pip install reportlab"
        ) from exc

    report_data = load_run_report_data(run_id)
    summary_df = report_data["summary"]
    summary = summary_df.iloc[0].to_dict() if not summary_df.empty else {}
    results_df = report_data["results"]
    alerts_df = report_data["alerts"]
    sla_df = report_data["sla_results"]

    output = BytesIO()
    document = SimpleDocTemplate(output, pagesize=letter)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Data Quality Executive Summary", styles["Title"]),
        Paragraph(f"Run ID: {run_id}", styles["Heading2"]),
        Spacer(1, 12),
    ]

    open_alerts = _open_alert_count(alerts_df)
    sla_status = _sla_status(sla_df)
    summary_rows = [
        ["Quality Score", _format_value(summary.get("quality_score"), suffix="%")],
        ["Overall Status", _format_value(summary.get("overall_status"))],
        ["Total Checks", _format_value(summary.get("total_checks"))],
        ["Failed Checks", _format_value(summary.get("failed_checks"))],
        ["Critical Issues", _format_value(summary.get("critical_checks"))],
        ["Open Alerts", str(open_alerts)],
        ["SLA Status", sla_status],
    ]
    story.append(_styled_table(summary_rows, colors.HexColor("#E5E7EB")))
    story.append(Spacer(1, 16))

    story.append(Paragraph("Top Failed Datasets", styles["Heading2"]))
    top_failed = _top_failed_datasets(results_df)
    if top_failed:
        story.append(_styled_table([["Dataset", "Failed Checks"]] + top_failed, colors.HexColor("#FEE2E2")))
    else:
        story.append(Paragraph("No failed datasets for this run.", styles["BodyText"]))

    document.build(story)
    output.seek(0)
    data = output.getvalue()

    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        logger.info("Exported run %s PDF report to %s.", run_id, path)
        return path

    return data


def load_run_report_data(run_id: int) -> dict[str, pd.DataFrame]:
    """Load all report sections for a run from the monitoring database."""

    engine = create_monitor_engine()
    params = {"run_id": int(run_id)}

    queries = {
        "summary": """
            SELECT *
            FROM data_quality_runs
            WHERE run_id = :run_id
        """,
        "results": """
            SELECT *
            FROM data_quality_results
            WHERE run_id = :run_id
            ORDER BY id
        """,
        "failed_checks": """
            SELECT *
            FROM data_quality_results
            WHERE run_id = :run_id AND status = 'FAIL'
            ORDER BY severity DESC, failed_rows DESC, id
        """,
        "issue_details": """
            SELECT *
            FROM data_quality_issue_details
            WHERE run_id = :run_id
            ORDER BY id
        """,
        "alerts": """
            SELECT *
            FROM data_quality_alerts
            WHERE run_id = :run_id
            ORDER BY id
        """,
        "sla_results": """
            SELECT *
            FROM data_quality_sla_results
            WHERE run_id = :run_id
            ORDER BY id
        """,
        "profiles": """
            SELECT *
            FROM data_profile_results
            WHERE run_id = :run_id
            ORDER BY dataset_name, column_name, id
        """,
    }

    data = {
        key: _read_sql(query, engine, params)
        for key, query in queries.items()
    }
    data["lineage"] = pd.DataFrame(get_all_lineage_edges())
    return data


def _read_sql(query: str, engine: Any, params: dict[str, Any]) -> pd.DataFrame:
    """Read SQL into a DataFrame and return empty data on missing optional tables."""

    try:
        return pd.read_sql(text(query), engine, params=params)
    except Exception:
        logger.exception("Could not load report query.")
        return pd.DataFrame()


def _format_worksheet(worksheet) -> None:
    """Apply basic enterprise-friendly formatting to a worksheet."""

    worksheet.freeze_panes = "A2"
    worksheet.auto_filter.ref = worksheet.dimensions

    for cell in worksheet[1]:
        cell.font = cell.font.copy(bold=True)

    for column_cells in worksheet.columns:
        max_length = 10
        column_letter = column_cells[0].column_letter
        for cell in column_cells:
            value = "" if cell.value is None else str(cell.value)
            max_length = max(max_length, min(len(value), 60))
        worksheet.column_dimensions[column_letter].width = max_length + 2


def _safe_frame(df: Any) -> pd.DataFrame:
    """Return a DataFrame copy for export."""

    return df.copy() if isinstance(df, pd.DataFrame) else pd.DataFrame()


def _open_alert_count(alerts_df: pd.DataFrame) -> int:
    """Return unresolved alert count."""

    if alerts_df.empty or "is_resolved" not in alerts_df.columns:
        return 0
    resolved = alerts_df["is_resolved"].fillna(False)
    return int((~resolved.astype(bool)).sum())


def _sla_status(sla_df: pd.DataFrame) -> str:
    """Return a compact SLA status for the PDF."""

    if sla_df.empty or "sla_status" not in sla_df.columns:
        return "N/A"
    statuses = sla_df["sla_status"].fillna("UNKNOWN").astype(str).str.upper()
    return "FAIL" if (statuses != "PASS").any() else "PASS"


def _top_failed_datasets(results_df: pd.DataFrame) -> list[list[Any]]:
    """Return top failed datasets for the PDF summary table."""

    if results_df.empty or "status" not in results_df.columns:
        return []
    failed = results_df[results_df["status"].fillna("").astype(str).str.upper() == "FAIL"]
    if failed.empty or "dataset_name" not in failed.columns:
        return []
    grouped = failed.groupby("dataset_name").size().reset_index(name="failed_checks")
    grouped = grouped.sort_values("failed_checks", ascending=False).head(5)
    return grouped.values.tolist()


def _styled_table(rows: list[list[Any]], header_color) -> Any:
    """Build a reportlab table with basic styling."""

    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle

    table = Table(rows, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), header_color),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D1D5DB")),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def _format_value(value: Any, suffix: str = "") -> str:
    """Format optional scalar values for PDF display."""

    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "N/A"
    return f"{value}{suffix}"
