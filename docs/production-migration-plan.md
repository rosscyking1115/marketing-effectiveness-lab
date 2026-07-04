# Production Migration Plan — Marketing Effectiveness Lab → multi-tenant SaaS

Status: **approved plan, not yet started.** This repository is the open-source **engine**
(Apache-2.0). The commercial application is a separate, proprietary work.

## Decisions locked (from a structured grilling session)

| # | Decision | Choice |
| --- | --- | --- |
| 1 | End-state | Multi-tenant commercial SaaS |
| 2 | Architecture | FastAPI engine + Next.js frontend; Streamlit demoted to internal/demo |
| 3 | Tenant isolation | Shared Postgres + Row-Level Security (`tenant_id`); `access.py` RBAC on top |
| 4 | Identity | Clerk (organizations + SSO) → JWT `org_id` → `tenant_id` for RLS |
| 5 | Data ingestion | OAuth connectors first — v1 scoped to Google Ads; CSV-contract upload as fallback |
| 6 | Compliance | GDPR-ready now, EU/UK data residency, encryption, export/erasure, retention, DPAs |
| 7 | v1 slice | MMM → budget → brief core loop; defer CRM/customer-PII modules, extra connectors, billing |
| 8 | Licensing | Open-core: engine Apache-2.0 (this repo); product proprietary (separate private repo) |

## Target architecture

```
Next.js (Vercel, EU)  ──►  FastAPI API + async workers (Fly/Render, EU, Docker)
   │  Clerk auth                     │  imports the engine package, unchanged
   ▼                                 ▼
Clerk (orgs/SSO) ──JWT──► verify ──► Postgres (Neon, EU) + RLS      Redis (job queue)
                                     Object storage (R2/S3, EU)     Stripe (Phase 4)
```

The tested engine (`src/marketing_effectiveness_lab`) is consumed as a **versioned package
dependency** by the private product repo. RLS is the hard isolation boundary; `access.py`
is the role/approval/audit layer above it.

## Repository layout (open-core → two repos)

- **Public engine repo (this one):** Apache-2.0, published to a package index; the analytics
  core, unchanged.
- **Private product repo:** proprietary. Suggested internal structure:
  `apps/web` (Next.js), `apps/api` (FastAPI), `infra/`, depending on the engine package.

## Recommended stack defaults (adjustable)

- DB: Neon (serverless Postgres, EU) + RLS + Alembic migrations.
- Jobs: Arq (or Celery) + Redis (Upstash EU) — model fits and connector syncs run async.
- Storage: Cloudflare R2 (EU) or S3 `eu-west`, per-tenant prefix, envelope-encrypted; OAuth
  tokens in an encrypted vault.
- Hosting: Vercel (web, EU) + Fly.io/Render (API + workers, EU, Docker).
- Observability: Sentry + structured logs + uptime. CI/CD: extend the existing GitHub Actions.

## Phased roadmap

- **Phase 0 — Foundations:** private product repo skeleton, EU infra accounts, ADRs for the
  decisions above. (Do not flip the README "prototype" positioning until Phase 1 ships.)
- **Phase 1 — Auth + tenancy + storage:** Clerk orgs; Postgres schema with `tenant_id` + RLS;
  wire `access.py` to Clerk roles; encrypted storage; GDPR export/erasure/retention endpoints.
- **Phase 2 — Ingestion:** Google Ads OAuth connector (token vault, async sync) + CSV-contract
  upload fallback → per-tenant weekly assembly (existing pipeline).
- **Phase 3 — Modeling loop (v1 payoff):** async MMM run → contribution/ROI/uncertainty →
  budget recommendation → PDF brief → DB-backed artifact registry + persisted audit log.
- **Phase 4 — Commercialize:** Stripe billing/plans/usage; onboarding polish.
- **Phase 5 — Expand:** Meta/GA4 connectors, CRM/customer modules with PII controls,
  enterprise SSO/SAML.

## Skills to apply by phase (from the local skills index)

| Phase | Skills |
| --- | --- |
| 1 (API/auth/DB) | `fastapi-templates`, `better-auth-best-practices`, `postgresql-table-design`, `supabase-postgres-best-practices` (RLS), `database-migration` |
| 1–3 (security/GDPR) | `harden`, `security-best-practices` |
| 2–3 (frontend) | `next-best-practices`, `shadcn`, `web-design-guidelines`, `frontend-design` |
| all (CI/deploy) | `github-actions-templates`, `deploy-to-vercel`, `github-actions-docs` |
| all (testing) | `tdd`, `webapp-testing` / `playwright-best-practices` |
| planning/exec | `architecture-decision-records`, `to-issues`, `dispatching-parallel-agents` |
| Phase 4 | `stripe-integration` |

## Execution note

When building, dispatch parallel agents per lane (API/auth/RLS, Google Ads connector,
Next.js frontend, infra/CI), coordinating through the engine package and the API contract.

## Risks

- OAuth-first delays first real data (platform app review) — CSV fallback keeps a working loop.
- Multi-tenant SaaS + GDPR is months of solo effort plus ongoing ops/legal.
- Recurring cost floors across Clerk / Neon / Vercel / Fly / Stripe.

## Immediate next steps (for the next session)

1. Confirm or adjust the stack defaults.
2. Scaffold **Phase 0**: create the private product repo skeleton + FastAPI app that imports
   the engine; set up EU infra accounts (Clerk, Neon, Vercel, Fly).
3. Write ADRs for the eight decisions above.
