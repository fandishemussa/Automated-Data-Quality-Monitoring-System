"""Reusable enterprise Streamlit UI components."""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from ui.theme import get_brand_config, get_version


STATUS_STYLES = {
    "PASS": ("#DCFCE7", "#166534", "#BBF7D0"),
    "FAIL": ("#FEE2E2", "#991B1B", "#FECACA"),
    "WARNING": ("#FEF3C7", "#92400E", "#FDE68A"),
    "SKIPPED": ("#E0F2FE", "#075985", "#BAE6FD"),
    "INFO": ("#DBEAFE", "#1D4ED8", "#BFDBFE"),
    "UNKNOWN": ("#F1F5F9", "#475569", "#CBD5E1"),
}

SEVERITY_STYLES = {
    "CRITICAL": ("#7F1D1D", "#FFFFFF", "#991B1B"),
    "HIGH": ("#FFEDD5", "#9A3412", "#FDBA74"),
    "MEDIUM": ("#FEF3C7", "#92400E", "#FDE68A"),
    "LOW": ("#DBEAFE", "#1D4ED8", "#BFDBFE"),
    "INFO": ("#E0F2FE", "#075985", "#BAE6FD"),
    "NONE": ("#F1F5F9", "#475569", "#CBD5E1"),
    "UNKNOWN": ("#F1F5F9", "#475569", "#CBD5E1"),
}


def metric_card(label, value, delta=None, status="neutral") -> None:
    """Render a KPI metric card."""

    colors = {
        "success": "var(--brand-success)",
        "warning": "var(--brand-warning)",
        "error": "var(--brand-error)",
        "neutral": "var(--brand-accent)",
        "info": "var(--brand-primary)",
    }
    accent = colors.get(str(status).lower(), colors["neutral"])
    delta_html = f'<div class="metric-delta">{_escape(delta)}</div>' if delta else ""
    icon = _metric_icon(label)

    st.markdown(
        f"""
        <div class="metric-card" style="border-top:3px solid {accent};">
            <div>
                <div style="display:flex;align-items:center;justify-content:space-between;gap:0.5rem;">
                    <div class="metric-label">{_escape(label)}</div>
                    <span style="width:9px;height:9px;border-radius:999px;background:{accent};display:inline-block;"></span>
                </div>
                <div class="metric-value">{_escape(value)}</div>
            </div>
            <div style="display:flex;align-items:center;gap:0.45rem;">
                <span class="muted-text" style="font-size:0.86rem;">{icon}</span>
                {delta_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_badge(status) -> str:
    """Return HTML for a status badge."""

    normalized = str(status or "UNKNOWN").upper()
    if normalized in {"TRUE", "RESOLVED"}:
        normalized = "PASS"
    if normalized in {"FALSE", "OPEN"}:
        normalized = "FAIL"
    return _badge(normalized, STATUS_STYLES.get(normalized, STATUS_STYLES["UNKNOWN"]))


def severity_badge(severity) -> str:
    """Return HTML for a severity badge."""

    normalized = str(severity or "UNKNOWN").upper()
    return _badge(normalized, SEVERITY_STYLES.get(normalized, SEVERITY_STYLES["UNKNOWN"]))


def sla_badge(status) -> str:
    """Return HTML for an SLA status badge."""

    normalized = str(status or "UNKNOWN").upper()
    if normalized in {"MET", "PASS"}:
        normalized = "PASS"
    elif normalized in {"VIOLATION", "FAIL"}:
        normalized = "FAIL"
    return status_badge(normalized)


def alert_status_badge(is_resolved) -> str:
    """Return HTML for an alert resolved/open badge."""

    resolved = _truthy(is_resolved)
    label = "Resolved" if resolved else "Open"
    style = STATUS_STYLES["PASS"] if resolved else STATUS_STYLES["FAIL"]
    return _badge(label, style)


def section_header(title, subtitle=None) -> None:
    """Render a dashboard section heading."""

    subtitle_html = (
        f'<div class="section-subtitle">{_escape(subtitle)}</div>'
        if subtitle
        else ""
    )
    st.markdown(
        f"""
        <div style="margin:1.1rem 0 0.45rem;">
            <div class="section-heading">{_escape(title)}</div>
            {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def empty_state(title, message, action_text=None) -> None:
    """Render a polished empty state."""

    action_html = (
        f'<div style="margin-top:0.65rem;"><code>{_escape(action_text)}</code></div>'
        if action_text
        else ""
    )
    st.markdown(
        f"""
        <div class="empty-state">
            <div class="empty-state-title">{_escape(title)}</div>
            <div class="muted-text">{_escape(message)}</div>
            {action_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def warning_state(title, message) -> None:
    """Render a warning state."""

    st.markdown(
        f"""
        <div class="empty-state" style="border-color:#FDE68A;">
            <div class="empty-state-title">{_escape(title)}</div>
            <div class="muted-text">{_escape(message)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def error_state(title, message, fix_command=None) -> None:
    """Render an error state without exposing stack traces."""

    action = f"Recommended fix: {fix_command}" if fix_command else None
    empty_state(title, message, action)


def render_footer() -> None:
    """Render product footer with version and environment information."""

    brand = get_brand_config()
    current_year = datetime.now().year
    st.markdown(
        f"""
        <div class="enterprise-footer">
            {_escape(brand.app_name)} | Version {_escape(get_version())} |
            {_escape(brand.company_name)} | {_escape(brand.environment_name)} |
            {current_year}
        </div>
        """,
        unsafe_allow_html=True,
    )


def add_badge_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add simple display columns for statuses and severities in dataframes."""

    if df.empty:
        return df

    formatted = df.copy()

    if "status" in formatted.columns and "status_display" not in formatted.columns:
        formatted["status_display"] = formatted["status"].apply(_text_status)

    if "sla_status" in formatted.columns and "sla_display" not in formatted.columns:
        formatted["sla_display"] = formatted["sla_status"].apply(_text_status)

    if "severity" in formatted.columns and "severity_display" not in formatted.columns:
        formatted["severity_display"] = formatted["severity"].apply(_text_severity)

    if "is_resolved" in formatted.columns and "alert_state" not in formatted.columns:
        formatted["alert_state"] = formatted["is_resolved"].apply(
            lambda value: "Resolved" if _truthy(value) else "Open"
        )

    return formatted


def _badge(label: str, style: tuple[str, str, str]) -> str:
    """Build a status badge HTML fragment."""

    background, color, border = style
    return (
        f'<span class="status-badge" '
        f'style="background:{background};color:{color};border-color:{border};">'
        f"{_escape(label)}</span>"
    )


def _text_status(value) -> str:
    """Return a compact text status for dataframe display."""

    normalized = str(value or "UNKNOWN").upper()
    marker = {
        "PASS": "OK",
        "FAIL": "FAIL",
        "WARNING": "WARN",
        "SKIPPED": "SKIP",
    }.get(normalized, "INFO")
    return f"{marker} {normalized}"


def _text_severity(value) -> str:
    """Return compact severity text for dataframe display."""

    normalized = str(value or "UNKNOWN").upper()
    return f"{normalized}"


def _metric_icon(label) -> str:
    """Return a small font-safe icon for a KPI label."""

    normalized = str(label or "").lower()
    if "quality" in normalized:
        return "◇"
    if "status" in normalized:
        return "●"
    if "total" in normalized:
        return "□"
    if "failed" in normalized:
        return "!"
    if "critical" in normalized:
        return "▲"
    if "alert" in normalized:
        return "!"
    return "•"


def _truthy(value) -> bool:
    """Return truthiness for bool/string database values."""

    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    return bool(value)


def _escape(value: object) -> str:
    """Escape small HTML text fragments."""

    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
