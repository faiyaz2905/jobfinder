# Phase 3: Applied Tracking

Phase 3 improves posting status tracking in SQLite.

## Commands

Show recent postings:

```powershell
python -m radar history
```

Filter history by status:

```powershell
python -m radar history --status new
python -m radar history --status saved
python -m radar history --status applied
```

Filter history by company:

```powershell
python -m radar history --company ActionAid
```

Mark a posting as applied:

```powershell
python -m radar log-applied <posting-id>
python -m radar log-applied <posting-id> --note "Applied through company portal"
```

Set a broader status:

```powershell
python -m radar set-status <posting-id> saved --note "Review before applying"
python -m radar set-status <posting-id> interviewing
python -m radar set-status <posting-id> rejected
```

## Statuses

Supported statuses:

- `new`
- `saved`
- `applied`
- `interviewing`
- `rejected`
- `offer`
- `archived`

## Notes

- Existing databases are migrated automatically when the CLI opens them.
- `log-applied` records `applied_at` in UTC.
- `history` shows notes and applied timestamp when present.
- The old `applied` boolean remains in the database for compatibility, but `status` is now the main field.

