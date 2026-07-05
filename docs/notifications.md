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
