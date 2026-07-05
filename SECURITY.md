# Security Policy

## Secrets

Never commit `.env`, `.env.docker`, API keys, database passwords, webhook URLs, or local service credentials. Use `.env.example` and `.env.docker.example` as templates, then keep real values only on your machine, server, or secret manager.

## If A Secret Leaks

Rotate the leaked token or password immediately. Replace the value in your local environment, update any affected services, and review logs or repository history for accidental exposure.

## Safe Configuration

- Keep dashboard authentication enabled outside local demos.
- Use strong database passwords.
- Keep Slack, Teams, Mailtrap, SMTP, Snowflake, BigQuery, and Redshift credentials private.
- Prefer hashed dashboard passwords with `DASHBOARD_PASSWORD_HASH` when available.
- Do not include `.env`, logs, `.venv`, `__pycache__`, or release zips in commits.

## Reporting Issues

For private security issues, do not open a public issue with secrets or screenshots that reveal credentials. Share a minimal description and sanitized logs.
