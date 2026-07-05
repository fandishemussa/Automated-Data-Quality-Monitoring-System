"""Branding and theme helpers for the Streamlit dashboard."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class BrandConfig:
    """Dashboard branding settings loaded from environment variables."""

    app_name: str
    company_name: str
    dashboard_title: str
    dashboard_icon: str
    environment_name: str
    theme: str
    demo_mode: bool
    primary_color: str
    secondary_color: str
    accent_color: str
    success_color: str
    warning_color: str
    error_color: str
    logo_path: Path
    favicon_path: Path


def get_brand_config() -> BrandConfig:
    """Return dashboard branding configuration from environment variables."""

    demo_mode = _bool_env("DEMO_BRANDING_MODE", False)
    company_default = "Demo Company" if demo_mode else "Your Company"
    theme = os.getenv("DASHBOARD_THEME", "light").strip().lower()

    if theme not in {"light", "dark"}:
        theme = "light"

    return BrandConfig(
        app_name=os.getenv(
            "APP_NAME",
            "Automated Data Quality Monitoring System",
        ),
        company_name=os.getenv("COMPANY_NAME", company_default),
        dashboard_title=os.getenv("DASHBOARD_TITLE", "Data Quality Command Center"),
        dashboard_icon=_normal_icon(os.getenv("DASHBOARD_ICON", "⧉")),
        environment_name=os.getenv("ENVIRONMENT_NAME", "Development"),
        theme=theme,
        demo_mode=demo_mode,
        primary_color=os.getenv("BRAND_PRIMARY_COLOR", "#1E3A8A"),
        secondary_color=os.getenv("BRAND_SECONDARY_COLOR", "#0F172A"),
        accent_color=os.getenv("BRAND_ACCENT_COLOR", "#2563EB"),
        success_color=os.getenv("BRAND_SUCCESS_COLOR", "#16A34A"),
        warning_color=os.getenv("BRAND_WARNING_COLOR", "#F59E0B"),
        error_color=os.getenv("BRAND_ERROR_COLOR", "#DC2626"),
        logo_path=_project_path(os.getenv("BRAND_LOGO_PATH", "ui/assets/logo.png")),
        favicon_path=_project_path(os.getenv("BRAND_FAVICON_PATH", "ui/assets/favicon.png")),
    )


def inject_enterprise_css() -> None:
    """Inject safe CSS for the enterprise dashboard shell."""

    import streamlit as st

    brand = get_brand_config()
    palette = _palette(brand)

    st.markdown(
        f"""
        <style>
            :root {{
                --brand-primary: {brand.primary_color};
                --brand-secondary: {brand.secondary_color};
                --brand-accent: {brand.accent_color};
                --brand-success: {brand.success_color};
                --brand-warning: {brand.warning_color};
                --brand-error: {brand.error_color};
                --dashboard-bg: {palette["background"]};
                --surface: {palette["surface"]};
                --surface-muted: {palette["surface_muted"]};
                --border: {palette["border"]};
                --text-main: {palette["text"]};
                --text-muted: {palette["muted"]};
                --shadow: {palette["shadow"]};
            }}

            #MainMenu {{
                visibility: hidden;
            }}

            footer {{
                visibility: hidden;
            }}

            header {{
                visibility: hidden;
            }}

            .stApp {{
                background: var(--dashboard-bg);
                color: var(--text-main);
            }}

            section[data-testid="stSidebar"] {{
                background: {palette["sidebar"]};
                border-right: 1px solid var(--border);
            }}

            section[data-testid="stSidebar"] * {{
                color: {palette["sidebar_text"]};
            }}

            div[data-testid="stVerticalBlock"] {{
                gap: 0.85rem;
            }}

            .block-container {{
                padding-top: 0.85rem;
                padding-left: 1.35rem;
                padding-right: 1.35rem;
                max-width: 1440px;
            }}

            h1, h2, h3 {{
                color: var(--text-main);
                letter-spacing: 0;
            }}

            .enterprise-card,
            .metric-card,
            .section-shell,
            .empty-state {{
                background: var(--surface);
                border: 1px solid var(--border);
                border-radius: 8px;
                box-shadow: var(--shadow);
            }}

            .metric-card {{
                padding: 1rem 1.05rem;
                min-height: 120px;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
            }}

            .metric-label {{
                color: var(--text-muted);
                font-size: 0.78rem;
                font-weight: 700;
                letter-spacing: 0.05em;
                text-transform: uppercase;
            }}

            .metric-value {{
                color: var(--text-main);
                font-size: 1.72rem;
                font-weight: 800;
                line-height: 1.2;
                margin-top: 0.45rem;
                word-break: break-word;
            }}

            .metric-delta {{
                color: var(--text-muted);
                font-size: 0.82rem;
                margin-top: 0.35rem;
            }}

            .enterprise-header {{
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                gap: 1rem;
                padding: 1rem 1.15rem;
                margin-bottom: 1.15rem;
                background: var(--surface);
                border: 1px solid var(--border);
                border-radius: 10px;
                box-shadow: var(--shadow);
            }}

            .enterprise-title {{
                color: var(--text-main);
                font-size: 1.42rem;
                font-weight: 800;
                margin: 0;
            }}

            .enterprise-subtitle,
            .section-subtitle,
            .muted-text {{
                color: var(--text-muted);
            }}

            .brand-mark {{
                width: 42px;
                height: 42px;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                flex: 0 0 auto;
                border-radius: 12px;
                background: var(--brand-primary);
                color: white;
                font-weight: 800;
                overflow: hidden;
                letter-spacing: 0;
                line-height: 1;
                padding: 0;
            }}

            .brand-row {{
                display: flex;
                align-items: center;
                gap: 0.75rem;
            }}

            .sidebar-brand {{
                padding: 0.45rem 0 1rem;
                border-bottom: 1px solid rgba(148, 163, 184, 0.28);
                margin-bottom: 0.95rem;
            }}

            .sidebar-app-name {{
                font-size: 0.9rem;
                font-weight: 800;
                line-height: 1.2;
                max-width: 170px;
            }}

            .sidebar-company {{
                font-size: 0.78rem;
                opacity: 0.78;
            }}

            .env-pill {{
                display: inline-flex;
                align-items: center;
                border-radius: 999px;
                background: {palette["surface_muted"]};
                border: 1px solid var(--border);
                color: var(--text-muted);
                font-size: 0.7rem;
                font-weight: 700;
                margin-top: 0.65rem;
                padding: 0.18rem 0.48rem;
            }}

            .nav-group-label {{
                color: var(--text-muted);
                font-size: 0.72rem;
                font-weight: 800;
                letter-spacing: 0.07em;
                margin-top: 0.7rem;
                text-transform: uppercase;
            }}

            .sidebar-nav-list {{
                display: flex;
                flex-direction: column;
                gap: 0.18rem;
                margin: 0.25rem 0 0.7rem;
            }}

            .sidebar-nav-item {{
                display: flex;
                align-items: center;
                gap: 0.55rem;
                min-height: 38px;
                padding: 0.5rem 0.65rem;
                border-left: 3px solid transparent;
                border-radius: 8px;
                color: {palette["sidebar_text"]};
                font-size: 0.84rem;
                font-weight: 650;
                line-height: 1.1;
                text-decoration: none;
                transition: background 120ms ease, color 120ms ease, border-color 120ms ease;
            }}

            .sidebar-nav-item:hover {{
                background: {palette["surface_muted"]};
                color: var(--brand-accent);
                text-decoration: none;
            }}

            .sidebar-nav-item.active {{
                background: {palette["active_nav"]};
                border-left-color: var(--brand-accent);
                color: {palette["active_nav_text"]};
                font-weight: 800;
            }}

            .sidebar-nav-icon {{
                width: 1.15rem;
                display: inline-flex;
                justify-content: center;
                color: inherit;
                font-size: 0.92rem;
            }}

            .sidebar-user-card {{
                background: {palette["surface_muted"]};
                border: 1px solid var(--border);
                border-radius: 10px;
                margin: 0.8rem 0;
                padding: 0.7rem;
            }}

            .sidebar-user-name {{
                color: var(--text-main);
                font-size: 0.82rem;
                font-weight: 800;
            }}

            .sidebar-user-role {{
                color: var(--text-muted);
                font-size: 0.74rem;
                margin-top: 0.15rem;
            }}

            .status-badge {{
                display: inline-flex;
                align-items: center;
                gap: 0.35rem;
                padding: 0.22rem 0.55rem;
                border-radius: 999px;
                font-size: 0.74rem;
                font-weight: 800;
                border: 1px solid transparent;
                white-space: nowrap;
            }}

            .section-heading {{
                margin-top: 0.45rem;
                margin-bottom: 0.15rem;
                font-size: 1.12rem;
                font-weight: 800;
            }}

            .empty-state {{
                padding: 1.15rem;
                color: var(--text-main);
            }}

            .empty-state-title {{
                font-weight: 800;
                margin-bottom: 0.25rem;
            }}

            .stTabs [data-baseweb="tab-list"] {{
                gap: 0.35rem;
                border-bottom: 1px solid var(--border);
            }}

            .stTabs [data-baseweb="tab"] {{
                background: var(--surface-muted);
                border-radius: 8px 8px 0 0;
                padding: 0.55rem 0.85rem;
            }}

            div[data-testid="stDataFrame"] {{
                border: 1px solid var(--border);
                border-radius: 8px;
                overflow: hidden;
            }}

            div[data-testid="stDataFrame"] * {{
                font-size: 0.82rem;
            }}

            .stButton > button,
            .stDownloadButton > button,
            div[data-testid="stFormSubmitButton"] button {{
                border-radius: 8px;
                border: 1px solid var(--brand-accent);
                background: var(--brand-accent);
                color: white;
                font-weight: 700;
            }}

            section[data-testid="stSidebar"] .stButton > button {{
                background: transparent;
                border-color: #FCA5A5;
                color: #B91C1C;
                font-size: 0.78rem;
                min-height: 2.1rem;
            }}

            section[data-testid="stSidebar"] .stButton > button:hover {{
                background: #FEF2F2;
                border-color: #EF4444;
                color: #991B1B;
            }}

            .enterprise-footer {{
                color: var(--text-muted);
                border-top: 1px solid var(--border);
                font-size: 0.78rem;
                margin-top: 2rem;
                padding: 1rem 0 0.25rem;
            }}

            .login-card-brand {{
                text-align: center;
                margin-bottom: 1rem;
            }}

            .login-card-brand .brand-mark {{
                margin: 0 auto 0.8rem;
            }}

            .login-wrapper {{
                max-width: 440px;
                margin: 0 auto;
                padding: 1.4rem;
                background: var(--surface);
                border: 1px solid var(--border);
                border-radius: 14px;
                box-shadow: var(--shadow);
            }}

            .login-title {{
                color: var(--text-main);
                font-size: 1.35rem;
                font-weight: 800;
                margin-top: 0.25rem;
            }}

            .login-subtitle {{
                color: var(--text-muted);
                margin-bottom: 1rem;
            }}

            .login-access-note {{
                color: var(--text-muted);
                font-size: 0.8rem;
                margin-top: 0.9rem;
                text-align: center;
            }}

            @media (max-width: 900px) {{
                .enterprise-header {{
                    flex-direction: column;
                    align-items: stretch;
                }}

                .enterprise-header-meta {{
                    text-align: left !important;
                }}

                .block-container {{
                    padding-left: 1rem;
                    padding-right: 1rem;
                }}
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_app_header(
    status: str = "UNKNOWN",
    last_refresh: datetime | None = None,
    subtitle: str | None = None,
) -> None:
    """Render the top enterprise dashboard header."""

    import streamlit as st

    from ui.components import status_badge

    brand = get_brand_config()
    refresh_value = (last_refresh or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
    subtitle_text = subtitle or (
        "Enterprise Data Quality Monitoring Demo"
        if brand.demo_mode
        else brand.app_name
    )
    logo_html = _logo_html(brand, size=42)
    demo_badge = (
        '<span class="status-badge" style="background:#EFF6FF;color:#1D4ED8;border-color:#BFDBFE;">Demo Environment</span>'
        if brand.demo_mode
        else ""
    )

    st.markdown(
        f"""
        <div class="enterprise-header">
            <div class="brand-row">
                {logo_html}
                <div>
                    <div class="enterprise-title">{_escape(brand.dashboard_title)}</div>
                    <div class="enterprise-subtitle">{_escape(subtitle_text)}</div>
                </div>
            </div>
            <div class="enterprise-header-meta" style="text-align:right;padding-top:0.2rem;">
                <div>{status_badge(status)} {demo_badge}</div>
                <div class="muted-text" style="margin-top:0.35rem;">
                    {_escape(brand.company_name)} | {_escape(brand.environment_name)} | Last refresh {refresh_value}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_branding() -> None:
    """Render branded sidebar header."""

    import streamlit as st

    brand = get_brand_config()
    logo_html = _logo_html(brand, size=36)

    st.sidebar.markdown(
        f"""
        <div class="sidebar-brand">
            <div class="brand-row">
                {logo_html}
                <div>
                    <div class="sidebar-app-name">{_escape(brand.app_name)}</div>
                    <div class="sidebar-company">{_escape(brand.company_name)}</div>
                </div>
            </div>
            <div class="env-pill">{_escape(brand.environment_name)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def get_version() -> str:
    """Return product version from VERSION file, or dev when missing."""

    version_path = PROJECT_ROOT / "VERSION"
    if not version_path.exists():
        return "dev"

    version = version_path.read_text(encoding="utf-8").strip()
    return version or "dev"


def brand_mark_html(brand: BrandConfig | None = None, size: int = 42) -> str:
    """Return a logo/fallback brand mark for custom dashboard markup."""

    return _logo_html(brand or get_brand_config(), size=size)


def _palette(brand: BrandConfig) -> dict[str, str]:
    """Return light or dark color palette."""

    if brand.theme == "dark":
        return {
            "background": "#0B1120",
            "surface": "#111827",
            "surface_muted": "#1E293B",
            "border": "#334155",
            "text": "#F8FAFC",
            "muted": "#CBD5E1",
            "sidebar": "#020617",
            "sidebar_text": "#F8FAFC",
            "shadow": "0 10px 30px rgba(0,0,0,0.25)",
            "grid": "#334155",
            "active_nav": "#172554",
            "active_nav_text": "#DBEAFE",
        }

    return {
        "background": "#F8FAFC",
        "surface": "#FFFFFF",
        "surface_muted": "#F1F5F9",
        "border": "#E2E8F0",
        "text": "#0F172A",
        "muted": "#64748B",
        "sidebar": "#FFFFFF",
        "sidebar_text": "#0F172A",
        "shadow": "0 10px 24px rgba(15,23,42,0.06)",
        "grid": "#E2E8F0",
        "active_nav": "#EFF6FF",
        "active_nav_text": "#1D4ED8",
    }


def chart_palette() -> dict[str, str]:
    """Return theme-aware chart colors."""

    brand = get_brand_config()
    palette = _palette(brand)
    return {
        "primary": brand.primary_color,
        "secondary": brand.secondary_color,
        "accent": brand.accent_color,
        "success": brand.success_color,
        "warning": brand.warning_color,
        "error": brand.error_color,
        "text": palette["text"],
        "muted": palette["muted"],
        "grid": palette["grid"],
        "surface": palette["surface"],
    }


def _project_path(path_value: str) -> Path:
    """Resolve a project-relative asset path."""

    path = Path(path_value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _logo_html(brand: BrandConfig, size: int = 42) -> str:
    """Return HTML for the configured logo or a fallback mark."""

    if brand.logo_path.exists():
        import base64

        encoded = base64.b64encode(brand.logo_path.read_bytes()).decode("ascii")
        suffix = brand.logo_path.suffix.lower().lstrip(".") or "png"
        return (
            f'<span class="brand-mark" style="width:{size}px;height:{size}px;">'
            f'<img src="data:image/{suffix};base64,{encoded}" '
            f'style="width:78%;height:78%;object-fit:contain;display:block;" />'
            "</span>"
        )

    return (
        f'<span class="brand-mark" style="width:{size}px;height:{size}px;">'
        "▣</span>"
    )


def _normal_icon(value: str) -> str:
    """Normalize legacy emoji shortcodes used by older env files."""

    icon = (value or "").strip()
    if not icon or icon.startswith(":"):
        return "▣"
    return icon


def _escape(value: object) -> str:
    """Escape small HTML text fragments."""

    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _bool_env(key: str, default: bool = False) -> bool:
    """Read a boolean environment variable."""

    value = os.getenv(key)
    if value is None:
        return default
    return value.strip().lower() in {"true", "1", "yes", "y", "on"}
