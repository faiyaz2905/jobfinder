# Internship Radar Dashboard

Private React dashboard for the hosted Internship Radar application.

## Local development

Create an ignored `.env.local` in this directory:

```dotenv
VITE_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
VITE_SUPABASE_ANON_KEY=YOUR_SUPABASE_ANON_KEY
VITE_API_BASE_URL=http://localhost:3000
```

Install and run:

```powershell
npm.cmd install
npm.cmd run dev
```

Only the Supabase URL and anon key may use a `VITE_` prefix. Never put the
service-role key, SMTP password, cron secret, or database password in a Vite
environment variable.

Production is built from the repository root using `vercel.json`.

