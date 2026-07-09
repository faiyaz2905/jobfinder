# Internship Radar Deployment

The application code is ready for Vercel and Supabase. Account creation and
secret entry are intentionally manual because those actions grant access to
your email and production data.

## 1. Rotate the Gmail App Password

Delete the App Password previously shared in chat. Create a new App Password
for Internship Radar and keep it only in your password manager and Vercel.

## 2. Create Supabase

1. Create a Supabase project in a region near the intended Vercel function region.
2. Open **SQL Editor**.
3. Run `supabase/migrations/001_initial_schema.sql`.
4. Open **Authentication > URL Configuration**.
5. Set the Site URL to the final Vercel URL.
6. Add the Vercel URL to Redirect URLs.
7. Keep email magic-link authentication enabled.
8. Copy the project URL, anon key, and service-role key.

The service-role key is server-only. Never paste it into a `VITE_` variable.

## 3. Create Vercel Project

Deploy the repository root with the Vercel CLI or import the repository into
Vercel. The included `vercel.json` builds `radar-dashboard` and exposes the
Python API.

Add every variable from `.env.example` under **Project Settings > Environment
Variables**. Use production values only in the Production environment.

Generate `CRON_SECRET` with at least 32 random characters. Set `APP_ORIGIN` to
the exact production origin, without a trailing slash.

Set `ALLOWED_USER_EMAILS` and `RADAR_EMAIL_TO` to the private recipient email
addresses in Vercel only. Keep real addresses out of public example files.

## 4. Choose Scheduling Plan

The checked-in `vercel.json` contains three daily schedules:

- 02:00 UTC / 08:00 Asia/Dhaka
- 08:00 UTC / 14:00 Asia/Dhaka
- 14:00 UTC / 20:00 Asia/Dhaka

This configuration requires Vercel Pro. Vercel Hobby rejects schedules that
run more than once per day. On Hobby, remove the `crons` array and configure a
trusted external scheduler to call:

```text
GET https://YOUR_PROJECT.vercel.app/api/cron/scan
Authorization: Bearer YOUR_CRON_SECRET
```

Never place the cron secret in the URL.

## 5. Migrate Existing Local Data

Load `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` in the current PowerShell
session. Preview the migration:

```powershell
C:\Users\LENOVO\AppData\Local\Python\bin\python.exe scripts\migrate_sqlite_to_supabase.py
```

Then apply it:

```powershell
C:\Users\LENOVO\AppData\Local\Python\bin\python.exe scripts\migrate_sqlite_to_supabase.py --apply
```

The first cloud scan also seeds the company table when it is empty.

## 6. Production Verification

1. Sign in using one of the allowlisted email addresses.
2. Confirm `/api/session` returns only the signed-in email.
3. Run one manual scan.
4. Confirm postings and scan health survive a redeployment.
5. Confirm both recipients receive a test digest when a new posting exists.
6. Confirm a request to `/api/cron/scan` without the secret returns `401`.
7. Review Vercel logs and verify that no secrets or authorization headers appear.
