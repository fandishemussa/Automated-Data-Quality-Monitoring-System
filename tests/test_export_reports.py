from pathlib import Path

import openpyxl
import pandas as pd

from reports.export_reports import export_run_to_excel


def test_export_run_to_excel_creates_expected_sheets(tmp_path, monkeypatch):
    def fake_report_data(run_id):
        return {
            "summary": pd.DataFrame([{
                "run_id": run_id,
                "quality_score": 98.5,
                "overall_status": "PASS",
            }]),
            "results": pd.DataFrame([{
                "dataset_name": "customers",
                "check_type": "not_null_columns",
                "status": "PASS",
            }]),
            "failed_checks": pd.DataFrame(),
            "issue_details": pd.DataFrame(),
            "alerts": pd.DataFrame(),
            "sla_results": pd.DataFrame(),
            "profiles": pd.DataFrame(),
            "lineage": pd.DataFrame([{
                "source_table": "customers",
                "target_table": "orders",
            }]),
        }

    monkeypatch.setattr("reports.export_reports.load_run_report_data", fake_report_data)

    output_path = tmp_path / "executive_report.xlsx"
    result_path = export_run_to_excel(101, output_path)

    assert result_path == output_path
    assert output_path.exists()

    workbook = openpyxl.load_workbook(output_path)
    assert workbook.sheetnames == [
        "Executive Summary",
        "Check Results",
        "Failed Checks",
        "Issue Details",
        "Alerts",
        "SLA Results",
        "Data Profiling",
        "Lineage",
    ]

    summary_sheet = workbook["Executive Summary"]
    assert summary_sheet.freeze_panes == "A2"
    assert summary_sheet["A1"].font.bold
    assert summary_sheet.auto_filter.ref is not None


def test_export_run_to_excel_returns_bytes(monkeypatch):
    monkeypatch.setattr(
        "reports.export_reports.load_run_report_data",
        lambda run_id: {
            "summary": pd.DataFrame([{"run_id": run_id}]),
            "results": pd.DataFrame(),
            "failed_checks": pd.DataFrame(),
            "issue_details": pd.DataFrame(),
            "alerts": pd.DataFrame(),
            "sla_results": pd.DataFrame(),
            "profiles": pd.DataFrame(),
            "lineage": pd.DataFrame(),
        },
    )

    data = export_run_to_excel(202)

    assert isinstance(data, bytes)
    assert data.startswith(b"PK")
