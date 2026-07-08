# Changelog

## v2.3.0

- Hardened the Enterprise Data Remediation Center workflow from open issue through preview, job creation, approval, execution, change history, verification, and resolution.
- Added backend-enforced role permissions for cleaning jobs, alert operations, issue lifecycle updates, assignment, rollback, and read-only viewer access.
- Added `data_engineer` role support for operational remediation without admin-only approval or assignment permissions.
- Scoped `data_analyst` users to alerts, issues, and cleaning jobs assigned to their username.
- Enforced cleaning policy checks for allowed actions, restricted actions, approval requirements, source update controls, and row limits.
- Recorded source before/after change history before execution so every source update is auditable and rollback-ready.
- Improved Data Remediation Center controls with permission-aware buttons and assigned-work messaging.
- Added remediation API documentation covering authentication, role permissions, endpoints, and lifecycle states.

## v1.0.0

- Added professional Streamlit dashboard with authentication, exports, alert resolution, profiling, drift, lineage, SLA tracking, and operational alert ownership.
- Added PostgreSQL monitoring database initialization, demo data seeding, logging, configuration validation, and a full CLI.
- Added Slack, Microsoft Teams, Mailtrap, Airflow, FastAPI, Docker, Redshift/source connector support, and release packaging.
- Added release safety files, example configuration templates, and expanded documentation.
