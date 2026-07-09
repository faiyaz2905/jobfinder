# Phase 4: Contact Repository

Phase 4 adds a public contact-email repository for outreach research.

## Commands

Refresh contacts for all tracked companies:

```powershell
python -m radar contacts update
```

Refresh one company while testing:

```powershell
python -m radar contacts update --company ActionAid
```

Limit how many pages are checked per company:

```powershell
python -m radar contacts update --company WaterAid --max-pages 4
```

List stored contacts:

```powershell
python -m radar contacts list
python -m radar contacts list --company WaterAid
python -m radar contacts list --type hr
```

Export contacts to CSV:

```powershell
python -m radar contacts export
python -m radar contacts export --output outreach-contacts.csv
python -m radar contacts export --type hr
```

## Stored Fields

The `contacts` table stores:

- `company`
- `email`
- `contact_type`
- `source_page`
- `date_scraped`
- `first_seen`
- `last_seen`

Contacts are deduped by company and email.

## Contact Types

- `hr`: addresses that appear related to HR, careers, jobs, recruitment, or talent
- `named`: likely personal emails based on local-part shape
- `generic`: fallback addresses such as `info@`, `contact@`, or `admin@`

## Notes

- The scraper only uses public pages.
- It checks the configured career URL plus likely contact/about/career pages on the same domain.
- Missing pages and 404s are skipped so one bad candidate URL does not stop the company scan.
- The repository is meant for targeted, personalized outreach, not bulk email blasts.

