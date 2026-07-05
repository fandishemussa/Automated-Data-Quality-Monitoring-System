"""FastAPI backend for monitoring data quality results."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from data_sources.postgres_connector import create_monitor_engine
from utils.logger import get_logger


logger = get_logger(__name__)

app = FastAPI(
    title="Automated Data Quality Monitoring API",
    version="1.0.0",
    description="Read monitoring runs, results, issue details, and alerts.",
)


def _database_unavailable_error() -> HTTPException:
    """Return a friendly API error for database connectivity failures."""

    return HTTPException(
        status_code=503,
        detail="Database is unavailable. Check .env settings and PostgreSQL status.",
    )


def fetch_all(query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Execute a SELECT query and return JSON-friendly dictionaries."""

    try:
        engine = create_monitor_engine()
        with engine.begin() as connection:
            rows = connection.execute(text(query), params or {}).mappings().all()
    except SQLAlchemyError:
        logger.exception("API database query failed.")
        raise _database_unavailable_error()
    except Exception:
        logger.exception("Unexpected API query error.")
        raise _database_unavailable_error()

    return jsonable_encoder([dict(row) for row in rows])


def fetch_one(query: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Execute a SELECT query and return one JSON-friendly row."""

    rows = fetch_all(query, params)
    return rows[0] if rows else None


@app.get("/health")
def health() -> dict[str, str]:
    """Return a basic API health response."""

    return {"status": "ok", "service": "data-quality-monitoring-api"}


@app.get("/runs")
def get_runs(limit: int = Query(100, ge=1, le=1000)) -> list[dict[str, Any]]:
    """Return recent data quality runs."""

    return fetch_all(
        """
        SELECT *
        FROM data_quality_runs
        ORDER BY run_id DESC
        LIMIT :limit
        """,
        {"limit": limit},
    )


@app.get("/runs/latest")
def get_latest_run() -> dict[str, Any]:
    """Return the latest data quality run."""

    row = fetch_one(
        """
        SELECT *
        FROM data_quality_runs
        ORDER BY run_id DESC
        LIMIT 1
        """
    )

    if row is None:
        raise HTTPException(status_code=404, detail="No data quality runs found.")

    return row


@app.get("/results")
def get_results(limit: int = Query(500, ge=1, le=5000)) -> list[dict[str, Any]]:
    """Return recent data quality check results."""

    return fetch_all(
        """
        SELECT *
        FROM data_quality_results
        ORDER BY id DESC
        LIMIT :limit
        """,
        {"limit": limit},
    )


@app.get("/results/{run_id}")
def get_results_for_run(run_id: int) -> list[dict[str, Any]]:
    """Return data quality check results for one run."""

    return fetch_all(
        """
        SELECT *
        FROM data_quality_results
        WHERE run_id = :run_id
        ORDER BY id DESC
        """,
        {"run_id": run_id},
    )


@app.get("/issues/{run_id}")
def get_issues_for_run(run_id: int) -> list[dict[str, Any]]:
    """Return issue-detail examples for one run."""

    return fetch_all(
        """
        SELECT *
        FROM data_quality_issue_details
        WHERE run_id = :run_id
        ORDER BY id DESC
        """,
        {"run_id": run_id},
    )


@app.get("/alerts")
def get_alerts(
    limit: int = Query(500, ge=1, le=5000),
) -> list[dict[str, Any]]:
    """Return recent alerts."""

    return fetch_all(
        """
        SELECT *
        FROM data_quality_alerts
        ORDER BY id DESC
        LIMIT :limit
        """,
        {"limit": limit},
    )


@app.patch("/alerts/{alert_id}/resolve")
def resolve_alert(alert_id: int) -> dict[str, Any]:
    """Mark one alert as resolved."""

    query = text(
        """
        UPDATE data_quality_alerts
        SET
            is_resolved = TRUE,
            resolved_at = CURRENT_TIMESTAMP
        WHERE id = :alert_id
        """
    )

    try:
        engine = create_monitor_engine()
        with engine.begin() as connection:
            result = connection.execute(query, {"alert_id": alert_id})
    except SQLAlchemyError:
        logger.exception("API could not resolve alert %s.", alert_id)
        raise _database_unavailable_error()
    except Exception:
        logger.exception("Unexpected API error resolving alert %s.", alert_id)
        raise _database_unavailable_error()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Alert not found.")

    return {"alert_id": alert_id, "is_resolved": True}
