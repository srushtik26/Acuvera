# Acuvera — Engineering Specification (Source of Truth)

> Acuvera is an India-optimized Emergency Department Operational Intelligence & Triage Optimization Platform.
> This file is the canonical source of truth for all implementation, testing, and acceptance decisions.

See the full specification document provided by the product owner.

## MVP Stack (Active Constraints)

| Concern | Solution |
|---|---|
| Backend | Django 4.x + DRF |
| Database | PostgreSQL 14+ (psycopg3) |
| Background jobs | APScheduler (in-process, no Celery/Redis) |
| Concurrency | `transaction.atomic` + `SELECT FOR UPDATE` + optimistic locking |
| Auth | Clerk JWT (adapter interface for SAML/LDAP swap) |
| LLM | GROQ Cloud API (feature-flagged, PHI-sanitized) |
| Frontend | React + Vite + PWA |
| Deployment | Single gunicorn process + PostgreSQL |

## Non-goals (do not implement)

- Medical diagnosis / treatment recommendations
- Mortality prediction models
- Autonomous medical decisions
- Self-hosted LLM training
- Replacement of existing EHRs
