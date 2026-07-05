"""Enterprise Altair chart styling helpers."""

from __future__ import annotations

import altair as alt

from ui.theme import chart_palette

ENTERPRISE_CHART_COLORS = {
    "blue": "#2563EB",
    "green": "#16A34A",
    "amber": "#F59E0B",
    "red": "#DC2626",
    "slate": "#475569",
    "light_blue": "#DBEAFE",
    "light_red": "#FEE2E2",
}


def apply_enterprise_chart_theme(chart, height=320):
    """Apply consistent enterprise chart styling."""

    colors = chart_palette()
    return (
        chart.properties(height=height, background="transparent")
        .configure_view(strokeWidth=0)
        .configure_axis(
            gridColor=colors["grid"],
            labelColor=colors["muted"],
            titleColor=colors["text"],
            labelFontSize=11,
            titleFontSize=12,
            gridOpacity=0.65,
            domain=False,
            tickColor=colors["grid"],
        )
        .configure_legend(
            orient="top",
            title=None,
            labelColor=colors["text"],
            labelFontSize=11,
            symbolSize=90,
        )
        .configure_title(
            color=colors["text"],
            fontSize=14,
            fontWeight="bold",
        )
    )


def severity_color_scale():
    """Return an Altair severity color scale."""

    colors = chart_palette()
    return alt.Scale(
        domain=["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO", "NONE", "UNKNOWN"],
        range=[
            "#991B1B",
            ENTERPRISE_CHART_COLORS["red"],
            ENTERPRISE_CHART_COLORS["amber"],
            ENTERPRISE_CHART_COLORS["blue"],
            "#0EA5E9",
            "#94A3B8",
            ENTERPRISE_CHART_COLORS["slate"],
        ],
    )


def score_band_color_scale():
    """Return an Altair quality-score band color scale."""

    colors = chart_palette()
    return alt.Scale(
        domain=["Healthy", "Watch", "Needs attention"],
        range=[
            ENTERPRISE_CHART_COLORS["green"],
            ENTERPRISE_CHART_COLORS["amber"],
            ENTERPRISE_CHART_COLORS["red"],
        ],
    )
