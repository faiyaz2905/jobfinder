# Phase 5: LinkedIn and Facebook Discovery

Phase 5 adds optional, lower-confidence discovery sources.

## LinkedIn Discovery

LinkedIn is not scraped directly. The CLI uses SerpAPI to run search-engine queries for LinkedIn job URLs.

Required environment variable:

```powershell
$env:SERPAPI_API_KEY = "your-serpapi-key"
```

Run LinkedIn discovery:

```powershell
python -m radar discover linkedin
python -m radar discover linkedin --company ActionAid
python -m radar discover linkedin --notify
```

Include LinkedIn discovery during a normal scan:

```powershell
python -m radar scan --include-linkedin
python -m radar scan --include-linkedin --notify
```

Optional query tuning:

```powershell
$env:RADAR_LINKEDIN_QUERY_SUFFIX = "intern OR internship Bangladesh"
```

## Facebook Discovery

Facebook discovery uses the Meta Graph API for configured public Page URLs.

Required environment variable:

```powershell
$env:META_GRAPH_ACCESS_TOKEN = "your-meta-graph-token"
```

Each company also needs a Facebook page URL in config. You can add one when adding or replacing a company:

```powershell
python -m radar add-company "Example Co" --career-url "https://example.com/careers" --facebook-page-url "https://www.facebook.com/exampleco"
```

Run Facebook discovery:

```powershell
python -m radar discover facebook
python -m radar discover facebook --company "Example Co"
```

Include Facebook discovery during a normal scan:

```powershell
python -m radar scan --include-facebook
```

## Combined Discovery

```powershell
python -m radar discover all
python -m radar scan --include-linkedin --include-facebook --notify
```

## Notes

- LinkedIn results are stored with source `linkedin`.
- Facebook results are stored with source `facebook`.
- Both paths dedupe through the same SQLite postings table.
- Missing API keys produce a clear error and do not stop the rest of the command.
- Discovery results are lower-confidence than direct career-page/ATS results.

