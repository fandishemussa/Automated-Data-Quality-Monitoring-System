"""Build a safe downloadable release ZIP."""

from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RELEASE_DIR = PROJECT_ROOT / "release"

ROOT_FILES = [
    ".dockerignore",
    ".env.example",
    ".env.docker.example",
    ".gitignore",
    "CHANGELOG.md",
    "Dockerfile",
    "LICENSE",
    "QUICKSTART.md",
    "README.md",
    "SECURITY.md",
    "VERSION",
    "cli.py",
    "docker-compose.yml",
    "docker-compose.airflow.yml",
    "main.py",
    "requirements.txt",
    "requirements-airflow.txt",
    "requirements-bigquery.txt",
    "requirements-snowflake.txt",
]

INCLUDE_DIRS = [
    "airflow",
    "alerts",
    "api",
    "auth",
    "checks",
    "config",
    "connectors",
    "dashboard",
    "data_sources",
    "database",
    "docs",
    "lineage",
    "notifications",
    "reports",
    "scripts",
    "sla",
    "tests",
    "ui",
    "utils",
]

EXCLUDED_PARTS = {
    ".agents",
    ".git",
    ".idea",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "htmlcov",
    "logs",
    "release",
}
EXCLUDED_NAMES = {".env", ".env.docker", ".coverage"}
EXCLUDED_SUFFIXES = {".log", ".pyc", ".pyo", ".zip"}


def read_version() -> str:
    """Read the release version from VERSION."""

    version_file = PROJECT_ROOT / "VERSION"
    if not version_file.exists():
        return "0.0.0"
    return version_file.read_text(encoding="utf-8").strip()


def should_include(path: Path) -> bool:
    """Return True when a path is safe for the release archive."""

    relative = path.relative_to(PROJECT_ROOT)

    if any(part in EXCLUDED_PARTS for part in relative.parts):
        return False
    if path.name in EXCLUDED_NAMES:
        return False
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False

    return path.is_file()


def iter_release_files() -> list[Path]:
    """Return sorted source files that belong in the release."""

    files: set[Path] = set()

    for file_name in ROOT_FILES:
        path = PROJECT_ROOT / file_name
        if should_include(path):
            files.add(path)

    for directory_name in INCLUDE_DIRS:
        directory = PROJECT_ROOT / directory_name
        if not directory.exists():
            continue
        for path in directory.rglob("*"):
            if should_include(path):
                files.add(path)

    return sorted(files)


def build_release_zip() -> Path:
    """Create the release ZIP and return its path."""

    version = read_version()
    RELEASE_DIR.mkdir(exist_ok=True)
    archive_path = RELEASE_DIR / f"automated-data-quality-monitor-v{version}.zip"

    with ZipFile(archive_path, "w", ZIP_DEFLATED) as archive:
        for path in iter_release_files():
            archive.write(path, path.relative_to(PROJECT_ROOT).as_posix())

    return archive_path


def main() -> int:
    """Build the release archive."""

    archive_path = build_release_zip()
    print(f"Release archive created: {archive_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
