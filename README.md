# Breathe ESG Prototype

Prototype for the Breathe ESG tech intern assignment.

## What’s included

- Django REST API for normalized ingestion and analyst review
- React dashboard for queue review, edits, approvals, and audit trail inspection
- Seeded demo tenant with SAP, utility, and travel rows
- Submission docs: `MODEL.md`, `DECISIONS.md`, `TRADEOFFS.md`, `SOURCES.md`

## Local run

Backend:

```bash
Push-Location backend
c:/Users/Anurag/Desktop/hi/.venv/Scripts/python.exe manage.py migrate
c:/Users/Anurag/Desktop/hi/.venv/Scripts/python.exe manage.py seed_demo
c:/Users/Anurag/Desktop/hi/.venv/Scripts/python.exe manage.py runserver 127.0.0.1:8000
Pop-Location
```

Frontend:

```bash
Push-Location frontend
npm install
npm run dev
Pop-Location
```

The frontend proxies `/api` to the Django server at `127.0.0.1:8000`.

## Notes

- The frontend loads demo data through the API if the database is empty.
- The data model is intentionally simple and audit-friendly rather than over-normalized.
