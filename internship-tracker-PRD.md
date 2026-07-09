# Product Requirements Document: Internship Radar

**Author:** Faiyaz  
**Status:** Draft v2.0 - Vercel deployment target  
**Date:** July 2026  
**Target user:** Solo user, IBA finance student entering the internship and job market after August 2026

---

## 1. Overview

Internship Radar is a private online dashboard that monitors a curated list of companies for internship and entry-level job postings. It checks company career pages and supported public sources, stores results in a hosted database, and sends email alerts when genuinely new opportunities appear.

The production application is hosted on Vercel and is designed to run without the user's computer being switched on. A protected scheduled endpoint runs the scan three times each day. The existing command-line interface remains useful for local development and manual maintenance, but it is no longer the production runtime.

## 2. Problem Statement

Manually checking target companies several times every day is time-consuming and makes it easy to miss short-lived opportunities. A local scheduler is not sufficient because it stops whenever the user's computer is off or disconnected.

The product needs:

- A dashboard available from a phone or computer.
- Automated scans three times per day.
- Persistent cloud storage shared by scans and the dashboard.
- Reliable email notifications sent to both configured recipients.
- Secure handling of SMTP, database, scheduler, and authentication secrets.

## 3. Goals

- **G1:** Detect new internship and entry-level postings for a user-managed company list.
- **G2:** Run automatically three times per day without depending on a personal computer.
- **G3:** Show postings, contacts, scan health, and applied status in a private web dashboard.
- **G4:** Provide a direct application URL or `mailto:` action for each posting.
- **G5:** Email a digest to the configured private recipient list when new postings are found.
- **G6:** Prevent duplicate notifications and preserve scan history in a hosted database.
- **G7:** Keep all privileged credentials server-side and out of source control, browser bundles, and logs.
- **G8:** Retain a local development workflow for testing scans before production deployment.

### Non-goals

- Automatically submitting job applications.
- Direct scraping of authenticated LinkedIn or Facebook pages.
- Bulk cold-email campaigns.
- A public multi-user SaaS product.
- Storing CVs, government IDs, or other sensitive application documents.

## 4. User Stories

1. As the user, I can securely open the dashboard from my phone and see newly found opportunities.
2. As the user, I receive an email digest when a scheduled scan discovers new postings.
3. As the user, I can run a manual scan from the dashboard when needed.
4. As the user, I can mark a posting as applied and preserve that status across devices.
5. As the user, I can review the last scan time, duration, source failures, and notification result.
6. As the user, I can view and export publicly listed company contact emails.
7. As the owner, I can add or disable companies without editing production secrets.
8. As the owner, I can run and test the project locally using separate development credentials.

## 5. Production Architecture

### 5.1 Components

1. **Web dashboard:** React frontend deployed on Vercel.
2. **Server API:** Vercel Functions that expose authenticated dashboard operations.
3. **Scan worker:** A server-side Vercel Function that runs the existing Python scraper logic.
4. **Database:** Supabase Postgres, replacing SQLite in production.
5. **Scheduler:** Vercel Cron on Pro, or an approved external scheduler on Hobby.
6. **Notifications:** Gmail SMTP using a dedicated App Password stored in Vercel environment variables.
7. **Authentication:** Single-user authentication protecting the dashboard and all non-cron API routes.

### 5.2 Data Flow

```text
Scheduler
  -> GET /api/cron/scan with scheduler authorization
  -> acquire database scan lock
  -> scrape configured sources with timeouts and bounded concurrency
  -> normalize and validate results
  -> upsert postings in Supabase
  -> email one digest containing only newly inserted postings
  -> record scan status and source errors
  -> release scan lock

Authenticated dashboard
  -> Vercel API routes
  -> Supabase
  -> postings, contacts, companies, and scan history
```

### 5.3 Repository Shape

```text
radar/                         # reusable Python scan and notification logic
radar-dashboard/               # React dashboard
api/
  cron/scan.py                 # protected scheduled scan endpoint
  postings.py                  # authenticated posting reads
  postings_apply.py            # authenticated applied-status update
  contacts.py                  # authenticated contact reads/export
  companies.py                 # authenticated company management
  health.py                    # authenticated scan health
supabase/
  migrations/                  # versioned Postgres schema and policies
vercel.json                    # functions, regions, and cron configuration
```

The exact routing layout may change to match Vercel's supported Python runtime, but the security boundaries and endpoint behavior are required.

## 6. Functional Requirements

### 6.1 Dashboard

The dashboard must provide:

- Posting list with company, role, source, first-seen time, and application action.
- Filters for new, unapplied, applied, company, and source.
- A mark-as-applied action with a confirmation state.
- Company list management with enable/disable controls.
- Contact repository view and CSV export.
- Health view showing the latest scan, source failures, duration, and notification status.
- A manual scan command protected by authentication and rate limiting.
- Clear loading, empty, stale-data, partial-failure, and API-error states.

### 6.2 Company Sources

Each company record supports:

- Name.
- Career page URL.
- ATS type and ATS identifier when known.
- LinkedIn company slug or search query.
- Optional public Facebook page URL.
- Enabled/disabled status.
- Source-specific scraper configuration.

ATS JSON APIs are preferred. Generic HTML scraping is used only when a stable API is unavailable.

### 6.3 Scan Engine

- Normalize every result into a common posting schema.
- Generate a deterministic fingerprint from stable posting fields.
- Use a database uniqueness constraint for deduplication.
- Set explicit connection and response timeouts for every external request.
- Use bounded concurrency to avoid overwhelming company sites.
- Apply per-domain request limits and a descriptive user agent.
- Retry transient errors with exponential backoff and a strict retry limit.
- Record a source error without failing the entire scan.
- Reject malformed or unsafe application URLs.
- Finish within the configured Vercel Function duration.

Browser automation must not be part of the default production scan. Playwright may be used only for specific sources after confirming that its deployment size, runtime, and reliability fit Vercel limits. Unsupported JS-heavy sources should use an official API, a lightweight connector, or be marked unsupported.

### 6.4 Posting Deduplication

- The database must enforce uniqueness on the posting fingerprint.
- New-posting detection must happen inside a transaction or atomic upsert.
- Concurrent or retried scan requests must not create duplicates.
- A posting is emailed only when its first insertion succeeds.
- Applied status must never be reset by later scans.

### 6.5 Notifications

- Send one digest per scan only when new postings exist.
- Send every notification to both required email addresses.
- Include company, role, source, date found, and a safe application link.
- Escape all scraped text before placing it in HTML email.
- Never include SMTP credentials or internal errors in the email.
- Record notification success or failure in scan history.
- A notification failure must not roll back newly discovered postings.
- A safe retry mechanism must avoid sending the same digest twice.

### 6.6 Contacts

- Extract only business contact details intentionally published on public company pages.
- Store company, email, source page, and discovery date.
- Deduplicate contacts case-insensitively.
- Do not automatically send outreach emails.
- CSV exports are available only to the authenticated user.

### 6.7 LinkedIn and Facebook

- Do not log in to, automate, or directly scrape authenticated platform pages.
- LinkedIn discovery may use an approved search API and is marked lower confidence.
- Facebook support is optional and uses an approved public API only.
- Platform failures must not block career-page scans.

## 7. API Requirements

All responses use JSON except CSV exports.

| Method | Route | Purpose | Protection |
|---|---|---|---|
| `GET` | `/api/postings` | List and filter postings | User session |
| `PATCH` | `/api/postings/{id}` | Update applied status | User session + CSRF/origin checks |
| `GET` | `/api/contacts` | List contacts | User session |
| `GET` | `/api/contacts/export` | Download CSV | User session |
| `GET/POST` | `/api/companies` | List or add companies | User session |
| `PATCH` | `/api/companies/{id}` | Update or disable a company | User session |
| `GET` | `/api/health` | Read scan health | User session |
| `POST` | `/api/scans` | Request a manual scan | User session + rate limit |
| `GET` | `/api/cron/scan` | Run a scheduled scan | Scheduler secret only |

The cron route must reject requests unless the `Authorization` header exactly matches `Bearer ${CRON_SECRET}`. User-facing API routes must never accept the cron secret as user authentication.

## 8. Hosted Data Model

Production uses Supabase Postgres. SQLite remains supported only for local development and one-time migration.

### 8.1 `companies`

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `name` | text | Unique normalized name |
| `career_url` | text | HTTPS URL |
| `ats_type` | text | Optional connector type |
| `ats_identifier` | text | Optional connector identifier |
| `linkedin_query` | text | Optional |
| `facebook_url` | text | Optional HTTPS URL |
| `enabled` | boolean | Default true |
| `created_at` | timestamptz | Server generated |
| `updated_at` | timestamptz | Server generated |

### 8.2 `postings`

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `fingerprint` | text | Unique |
| `company_id` | UUID | Foreign key |
| `role` | text | Required |
| `apply_action` | text | Validated HTTPS URL or `mailto:` |
| `source` | text | Career page, LinkedIn, or Facebook |
| `source_url` | text | Discovery page |
| `first_seen_at` | timestamptz | Server generated |
| `last_seen_at` | timestamptz | Updated by scans |
| `applied_at` | timestamptz | Null until applied |

### 8.3 `contacts`

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `company_id` | UUID | Foreign key |
| `email` | text | Normalized |
| `source_page` | text | HTTPS URL |
| `first_seen_at` | timestamptz | Server generated |

A unique index must cover normalized company and email.

### 8.4 `scan_runs`

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `trigger` | text | Scheduled or manual |
| `status` | text | Running, succeeded, partial, or failed |
| `started_at` | timestamptz | Required |
| `finished_at` | timestamptz | Nullable while running |
| `companies_checked` | integer | Summary |
| `new_postings` | integer | Summary |
| `notification_status` | text | Not needed, sent, or failed |
| `error_summary` | jsonb | Sanitized source errors |

### 8.5 `scan_locks`

A database-backed lock prevents overlapping scans. Locks must have an expiry so a timed-out function cannot block future scans permanently.

## 9. Authentication and Authorization

- The production dashboard is private.
- Use an established authentication provider supported by the chosen frontend and Supabase.
- Allow only the owner's approved email address or user ID.
- Deny unauthenticated access by default.
- Enforce authorization in server routes and database policies, not only in the frontend.
- Enable Row Level Security for tables exposed through the Supabase Data API.
- The browser may receive only the Supabase public/anon key when required by the auth design.
- The Supabase service-role key and database password are server-only.
- State-changing routes must validate origin and use same-site, secure cookies or equivalent CSRF protection.

## 10. Secret and Environment Management

The repository contains `.env.example` with names and descriptions only. Real values are entered manually in Vercel Project Settings and in a local ignored `.env` file.

Required production variables:

| Variable | Exposure | Purpose |
|---|---|---|
| `SUPABASE_URL` | Server; public only if auth requires it | Supabase project URL |
| `SUPABASE_ANON_KEY` | Public only when required | Restricted client access with RLS |
| `SUPABASE_SERVICE_ROLE_KEY` | Server only | Privileged scan/database operations |
| `DATABASE_URL` | Server only | Serverless/transaction-pooler Postgres URL if used |
| `CRON_SECRET` | Server only | Scheduled endpoint authorization |
| `RADAR_SMTP_HOST` | Server only | SMTP host |
| `RADAR_SMTP_PORT` | Server only | SMTP port |
| `RADAR_SMTP_USERNAME` | Server only | Gmail sender account |
| `RADAR_SMTP_PASSWORD` | Server only | Dedicated Gmail App Password |
| `RADAR_EMAIL_FROM` | Server only | Sender address |
| `RADAR_EMAIL_TO` | Server only | Both required recipients |
| `AUTH_SECRET` | Server only | Session signing/encryption |
| `ALLOWED_USER_EMAILS` | Server only | Dashboard allowlist |
| `SEARCH_API_KEY` | Server only | Optional LinkedIn search provider |
| `META_ACCESS_TOKEN` | Server only | Optional Facebook API |

Security requirements:

- Never prefix a secret with `VITE_`, `NEXT_PUBLIC_`, or another framework public-variable prefix.
- Never place secrets in `vercel.json`, committed files, screenshots, browser storage, API responses, or logs.
- Configure production, preview, and development variables separately.
- Preview deployments must not use production SMTP or production service-role credentials.
- Rotate any secret that has been pasted into chat, committed, logged, or otherwise exposed.
- Use a unique Gmail App Password for this application, not the Gmail account password.
- Redact credentials and query strings from exception reporting.

## 11. Scheduling and Vercel Constraints

The required cadence is three scans per day. Target times are:

- 08:00 Asia/Dhaka = 02:00 UTC.
- 14:00 Asia/Dhaka = 08:00 UTC.
- 20:00 Asia/Dhaka = 14:00 UTC.

Vercel cron expressions use UTC.

### 11.1 Supported Scheduling Options

**Preferred: Vercel Pro**

Configure three schedules against `/api/cron/scan`:

```json
{
  "crons": [
    { "path": "/api/cron/scan", "schedule": "0 2 * * *" },
    { "path": "/api/cron/scan", "schedule": "0 8 * * *" },
    { "path": "/api/cron/scan", "schedule": "0 14 * * *" }
  ]
}
```

**Budget option: Vercel Hobby plus an external scheduler**

Vercel Hobby permits a cron schedule only once per day. To retain three daily checks, use a reputable external scheduler to call the same HTTPS endpoint with the `Authorization: Bearer <CRON_SECRET>` header. The scheduler must support secret headers and TLS. The secret must not appear in the URL.

The application must not claim that three daily Vercel Cron executions work on Hobby.

### 11.2 Runtime Requirements

- The scan endpoint must complete within the active Vercel Function duration limit.
- The function region should be selected near the Supabase database region.
- External calls must have individual timeouts so one source cannot consume the full invocation.
- Large company sets may be split into deterministic batches if scans approach the limit.
- The function must return a non-2xx response for unauthorized calls and unrecoverable failures.
- Expected source failures may return a successful partial status after scan history is persisted.
- No correctness may depend on local files surviving between invocations.
- Temporary files may be used only within an invocation and must not contain long-lived secrets.

## 12. Safety and Reliability

### 12.1 SSRF and URL Safety

- Accept only `https://` source URLs, with documented exceptions if unavoidable.
- Reject localhost, link-local, private-network, metadata-service, and non-HTTP destinations.
- Revalidate redirects before following them.
- Limit redirects, response size, and content types.
- Store and display scraped HTML as text; never render it as trusted HTML.

### 12.2 Abuse Prevention

- Protect manual scans with authentication and a cooldown.
- Protect scheduled scans with `CRON_SECRET`.
- Use a database lock to prevent overlapping scheduled and manual scans.
- Rate-limit mutating API routes.
- Restrict CORS to the production dashboard origin.

### 12.3 Observability

- Persist every scan run and its outcome.
- Log structured event names, durations, counts, and sanitized error categories.
- Never log email credentials, database URLs, auth tokens, full request headers, or scraped personal data.
- Show a dashboard warning when no successful scan has completed within 12 hours.
- Send an operational alert after repeated total scan failures.

### 12.4 Backup and Recovery

- Use Supabase backups appropriate to the selected plan.
- Keep schema migrations in source control.
- Support CSV export of postings, contacts, and companies.
- Test restoration or migration before relying on the hosted database as the only copy.

## 13. Local Development

- Local development may use SQLite or a separate Supabase development project.
- Local secrets live in an ignored `.env` file.
- SMTP defaults to a disabled or dry-run mode locally.
- Automated tests must not contact real companies, send email, or mutate production data.
- Recorded fixtures or mocked HTTP responses cover scraper behavior.
- A manual production-like test uses a single known source before enabling all companies.

No GitHub Actions workflow is required. Deployment to Vercel can be performed through the Vercel CLI or a connected repository at the owner's discretion, but secrets must remain in Vercel settings.

## 14. Success Metrics

- Three scheduled scan attempts per day.
- At least 95% of scheduled scans complete successfully over 30 days.
- New supported-source postings are emailed within eight hours.
- No duplicate posting notifications during retries or concurrent invocations.
- Zero production secrets exposed to browser bundles or source control.
- Dashboard data remains available across deployments and function restarts.
- ATS-based sources achieve the highest practical recall, with source health visible.
- Email notifications consistently reach both required recipients.

## 15. Build Phases

1. **Phase 1 - Cloud foundation:** Create Supabase project, Postgres migrations, environment template, and development/production separation.
2. **Phase 2 - Storage migration:** Add a Postgres repository, atomic posting upserts, scan history, and database locking; migrate useful SQLite data.
3. **Phase 3 - Server API:** Implement authenticated postings, contacts, companies, applied-status, health, and manual-scan endpoints.
4. **Phase 4 - Production scan worker:** Adapt scrapers for Vercel timeouts and packaging; add the protected cron endpoint and idempotent notifications.
5. **Phase 5 - Dashboard integration:** Connect the React dashboard to the API and complete authentication, loading, error, and mobile states.
6. **Phase 6 - Scheduling:** Configure either Vercel Pro cron schedules or an approved external scheduler for three daily UTC invocations.
7. **Phase 7 - Security verification:** Test authorization, RLS, secret exposure, URL validation, rate limits, scan locks, and dependency vulnerabilities.
8. **Phase 8 - Deployment and burn-in:** Deploy production, run a limited-source test, enable all companies gradually, and monitor for seven days.

## 16. Acceptance Criteria

The hosted release is complete only when:

- The dashboard requires authentication and rejects non-owner accounts.
- Production data is stored in Supabase, not Vercel's local filesystem.
- Three scheduled scans are configured and visible in scheduler logs.
- The cron endpoint rejects missing or incorrect authorization.
- Two simultaneous scan requests result in only one active scan.
- A repeated posting is stored once and notified once.
- Both required recipients receive a test digest.
- Applied status survives redeployment.
- A failed source appears in scan health without preventing successful sources from saving.
- No secret appears in the built frontend, repository history, API output, or application logs.
- A scan completes within the configured function duration with the full enabled company list.
- The owner can export postings and contacts before production data is deleted or migrated.

## 17. Decisions Required Before Deployment

- Choose Vercel Pro or an external scheduler for the required three daily runs.
- Choose and configure the single-user authentication provider.
- Select the Supabase region and place Vercel Functions near it.
- Decide whether production will use the Supabase Data API or the serverless transaction pooler.
- Audit each company source and disable unsupported or unreliable scrapers.
- Rotate the previously shared Gmail App Password before adding the replacement to Vercel.

## 18. Reference Documentation

- Vercel Cron Jobs: https://vercel.com/docs/cron-jobs
- Vercel Cron usage and pricing: https://vercel.com/docs/cron-jobs/usage-and-pricing
- Vercel Cron security: https://vercel.com/docs/cron-jobs/manage-cron-jobs
- Vercel Function limits: https://vercel.com/docs/functions/limitations
- Supabase Postgres connections: https://supabase.com/docs/guides/database/connecting-to-postgres
- Supabase Row Level Security: https://supabase.com/docs/guides/database/postgres/row-level-security
