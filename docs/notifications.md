# Notifications

Notifications are optional and failures do not stop a data quality run.

## Mailtrap

```powershell
EMAIL_NOTIFICATIONS_ENABLED=true
MAILTRAP_API_TOKEN=your_token
ALERT_RECIPIENTS=receiver@example.com
```

## Slack

```powershell
SLACK_NOTIFICATIONS_ENABLED=true
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

## Microsoft Teams

```powershell
TEAMS_NOTIFICATIONS_ENABLED=true
TEAMS_WEBHOOK_URL=https://...
```

Keep webhook URLs and tokens out of source control.

## Alert Escalation

Escalation rules live in `config/alert_ownership.yaml`:

```yaml
escalation:
  CRITICAL:
    after_hours: 4
    escalation_level: 1
    notify_team: Data Platform
  HIGH:
    after_hours: 24
    escalation_level: 1
    notify_team: Data Governance
```

Run escalation manually:

```powershell
python cli.py escalate-alerts
```

The workflow escalates unresolved `CRITICAL` and `HIGH` alerts after their SLA window, sets `escalation_status`, `escalation_level`, and `escalated_at`, logs `ALERT_ESCALATED`, and attempts Slack, Teams, and email notifications when those channels are enabled.
