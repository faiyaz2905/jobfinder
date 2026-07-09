# Phase 6: Local Scheduling

Phase 6 is now configured for local-only operation.

## Local Commands

Print a Windows Task Scheduler command:

```powershell
python -m radar schedule local --every-hours 12
```

With LinkedIn discovery:

```powershell
python -m radar schedule local --every-hours 12 --include-linkedin
```

With LinkedIn and Facebook discovery:

```powershell
python -m radar schedule local --every-hours 12 --include-linkedin --include-facebook
```

## Recommended Local Setup

Use the working Python path on this machine:

```powershell
& 'C:\Users\LENOVO\AppData\Local\Python\bin\python.exe' -m radar scan --notify
```

For a first manual test:

```powershell
& 'C:\Users\LENOVO\AppData\Local\Python\bin\python.exe' -m radar notify-test
& 'C:\Users\LENOVO\AppData\Local\Python\bin\python.exe' -m radar notify-test --send
& 'C:\Users\LENOVO\AppData\Local\Python\bin\python.exe' -m radar scan --company ActionAid --notify
```

## Environment Policy

Set secrets in your shell/session, not in project files:

```powershell
$env:RADAR_SMTP_USERNAME = "your.email@gmail.com"
$env:RADAR_SMTP_PASSWORD = "your-gmail-app-password"
$env:RADAR_EMAIL_FROM = "your.email@gmail.com"
```

Optional:

```powershell
$env:SERPAPI_API_KEY = "your-serpapi-key"
$env:META_GRAPH_ACCESS_TOKEN = "your-meta-token"
```

## GitHub

This project is not configured to run through GitHub.

- No GitHub workflow should be used for normal operation.
- No GitHub push is needed.
- The generated GitHub Actions workflow file was removed from the workspace.
- The app stores local state in `.radar/radar.sqlite3`.

## Notes

- Local scheduling depends on your machine being awake and online.
- Scheduled scans use digest notifications, so a run with no new postings sends no email.
- The app password remains an environment detail only.

