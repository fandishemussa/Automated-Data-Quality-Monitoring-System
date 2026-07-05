# Release Guide

Run checks before packaging:

```powershell
python -m compileall .
pytest -q
python cli.py version
python cli.py release-audit
python scripts/build_release.py
```

Build a release archive:

```powershell
python cli.py build-release
```

The archive is created under `release/` and excludes:

- `.env`
- `.env.docker`
- `.venv`
- `logs`
- `__pycache__`
- `*.pyc`
- `.git`
- `.pytest_cache`
- old zip files
