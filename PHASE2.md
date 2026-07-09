# Phase 2: Notifications

Phase 2 adds opt-in email alerts for newly discovered postings.

## Commands

Preview email settings and render a sample HTML alert:

```powershell
python -m radar notify-test
```

Run a scan and email only if new postings are found:

```powershell
python -m radar scan --notify
```

Run a smaller scan while testing:

```powershell
python -m radar scan --company ActionAid --notify
```

## Environment Variables

For Gmail with an App Password:

```powershell
$env:RADAR_SMTP_HOST = "smtp.gmail.com"
$env:RADAR_SMTP_PORT = "587"
$env:RADAR_SMTP_USERNAME = "your.email@gmail.com"
$env:RADAR_SMTP_PASSWORD = "your-gmail-app-password"
$env:RADAR_EMAIL_FROM = "your.email@gmail.com"
```

Keep the real app password as an environment value only. Do not save it in this file, in code, or in Git.

`RADAR_SMTP_HOST` and `RADAR_SMTP_PORT` default to Gmail's SMTP server, so the required values are usually username, password, and sender.

Set every recipient with `RADAR_EMAIL_TO`, separated by commas. Keep real
recipient addresses in your local environment or Vercel settings only.

## Notes

- `radar scan --notify` sends one digest email per scan, not one email per posting.
- No email is sent when a scan finds no new postings.
- Secrets are read from environment variables and are not stored in the project files.
- The notification body includes posting ID, company, role, source, and an Apply link.
