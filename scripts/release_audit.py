"""Release-readiness checks for the project."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from zipfile import ZipFile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

REQUIRED_FILES = [
    ".dockerignore",
    ".env.example",
    ".env.docker.example",
    "CHANGELOG.md",
    "Dockerfile",
    "LICENSE",
    "QUICKSTART.md",
    "README.md",
    "SECURITY.md",
    "VERSION",
    "cli.py",
    "docker-compose.yml",
    "main.py",
    "requirements.txt",
    "config/rules.example.yaml",
    "config/dashboard_users.example.yaml",
    "utils/config_validator.py",
    "scripts/build_release.py",
    "scripts/release_audit.py",
]

REQUIRED_DOCS = [
    "docs/api_guide.md",
    "docs/installation.md",
    "docs/configuration.md",
    "docs/rules_guide.md",
    "docs/dashboard_guide.md",
    "docs/notifications.md",
    "docs/docker_setup.md",
    "docs/troubleshooting.md",
    "docs/release_guide.md",
]

REQUIRED_CLI_COMMANDS = {
    "validate-config",
    "init-db",
    "seed-demo",
    "run-checks",
    "dashboard",
    "api",
    "version",
    "demo",
    "build-release",
    "release-audit",
}

UNSAFE_PARTS = {
    ".env",
    ".env.docker",
    ".git",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "logs",
    "release",
}


def run_audit() -> list[dict[str, str]]:
    """Run release checks and return structured audit results."""

    results: list[dict[str, str]] = []
    results.append(_check_required_files())
    results.append(_check_required_docs())
    results.append(_check_cli_commands())
    results.append(_check_docker_compose())
    results.append(_check_release_zip_safety())
    return results


def print_audit_report(results: list[dict[str, str]]) -> None:
    """Print a compact release audit report."""

    print("Release audit report")
    print("--------------------")
    for result in results:
        print(f"[{result['status']}] {result['name']}: {result['message']}")
        if result["status"] != "PASS" and result.get("recommended_fix"):
            print(f"  Fix: {result['recommended_fix']}")


def _check_required_files() -> dict[str, str]:
    missing = [
        file_name
        for file_name in REQUIRED_FILES
        if not (PROJECT_ROOT / file_name).exists()
    ]

    if missing:
        return _fail(
            "required files",
            "Missing file(s): " + ", ".join(missing),
            "Create the missing release files.",
        )

    return _pass("required files", "All required release files exist.", "")


def _check_required_docs() -> dict[str, str]:
    missing = [
        file_name
        for file_name in REQUIRED_DOCS
        if not (PROJECT_ROOT / file_name).exists()
    ]

    if missing:
        return _fail(
            "documentation",
            "Missing doc file(s): " + ", ".join(missing),
            "Create the missing files under docs/.",
        )

    return _pass("documentation", "All required documentation files exist.", "")


def _check_cli_commands() -> dict[str, str]:
    try:
        from cli import build_parser

        parser = build_parser()
        subparser_action = next(
            action
            for action in parser._actions
            if isinstance(action, argparse._SubParsersAction)
        )
        commands = set(subparser_action.choices)
    except Exception as exc:
        return _fail(
            "cli commands",
            f"Could not inspect CLI commands: {exc.__class__.__name__}",
            "Run `python cli.py --help` and fix import errors.",
        )

    missing = sorted(REQUIRED_CLI_COMMANDS - commands)

    if missing:
        return _fail(
            "cli commands",
            "Missing command(s): " + ", ".join(missing),
            "Update cli.py with all release commands.",
        )

    return _pass("cli commands", "All required CLI commands are registered.", "")


def _check_docker_compose() -> dict[str, str]:
    compose_path = PROJECT_ROOT / "docker-compose.yml"
    if not compose_path.exists():
        return _fail(
            "docker compose",
            "docker-compose.yml is missing.",
            "Create docker-compose.yml.",
        )

    content = compose_path.read_text(encoding="utf-8")
    required_snippets = [
        ".env.docker",
        "5433:5432",
        "dashboard:",
        "api:",
        "runner:",
        "service_healthy",
    ]
    missing = [snippet for snippet in required_snippets if snippet not in content]

    if missing:
        return _fail(
            "docker compose",
            "Missing expected compose snippet(s): " + ", ".join(missing),
            "Update docker-compose.yml to match the release Docker flow.",
        )

    return _pass("docker compose", "Docker Compose release setup looks complete.", "")


def _check_release_zip_safety() -> dict[str, str]:
    release_dir = PROJECT_ROOT / "release"
    archives = sorted(release_dir.glob("*.zip")) if release_dir.exists() else []

    if not archives:
        return _warning(
            "release archive safety",
            "No release archive found yet.",
            "Run `python cli.py build-release`, then rerun this audit.",
        )

    latest_archive = archives[-1]

    try:
        with ZipFile(latest_archive) as archive:
            names = archive.namelist()
    except Exception as exc:
        return _fail(
            "release archive safety",
            f"Could not inspect release archive: {exc.__class__.__name__}",
            "Rebuild the release archive.",
        )

    unsafe_entries = [
        name
        for name in names
        if _is_unsafe_archive_entry(name)
    ]

    if unsafe_entries:
        preview = ", ".join(unsafe_entries[:10])
        return _fail(
            "release archive safety",
            "Unsafe archive entries found: " + preview,
            "Fix scripts/build_release.py exclusions and rebuild the release.",
        )

    return _pass(
        "release archive safety",
        f"Latest release archive is safe: {latest_archive.name}",
        "",
    )


def _is_unsafe_archive_entry(name: str) -> bool:
    parts = set(Path(name).parts)

    if parts & UNSAFE_PARTS:
        return True
    return name.endswith((".pyc", ".pyo", ".log", ".zip"))


def _pass(name: str, message: str, recommended_fix: str) -> dict[str, str]:
    return _result(name, "PASS", message, recommended_fix)


def _warning(name: str, message: str, recommended_fix: str) -> dict[str, str]:
    return _result(name, "WARNING", message, recommended_fix)


def _fail(name: str, message: str, recommended_fix: str) -> dict[str, str]:
    return _result(name, "FAIL", message, recommended_fix)


def _result(
    name: str,
    status: str,
    message: str,
    recommended_fix: str,
) -> dict[str, str]:
    return {
        "name": name,
        "status": status,
        "message": message,
        "recommended_fix": recommended_fix,
    }


def main() -> int:
    """Run release audit and return a process exit code."""

    results = run_audit()
    print_audit_report(results)
    return 1 if any(result["status"] == "FAIL" for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
