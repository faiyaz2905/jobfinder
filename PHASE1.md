# Phase 1: Core Scan Loop

This workspace now has the first usable CLI slice of Internship Radar.

## What works

- Seeded company config from `company_career_links.xlsx`
- `radar list-companies`
- `radar add-company`
- `radar remove-company`
- `radar scan`
- `radar history`
- `radar log-applied`
- SQLite state at `.radar/radar.sqlite3`
- Generic career-page link scraping
- Greenhouse and Lever connector hooks when a company is configured with `ats_type`

## Run Locally

The normal command shape is:

```powershell
python -m radar list-companies
python -m radar scan --company ActionAid
python -m radar history
```

On this machine, the working interpreter path during setup was:

```powershell
& 'C:\Users\LENOVO\AppData\Local\Python\bin\python.exe' -m radar list-companies
```

## Notes

- The current scraper uses only the Python standard library.
- Some global career sites render jobs with JavaScript or custom APIs, so they may need company-specific adapters after the first full audit.
- Network access was blocked inside the sandbox until explicitly allowed; local runs outside the sandbox should not need that approval step.

