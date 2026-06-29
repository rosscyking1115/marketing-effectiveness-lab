# Production and Security Roadmap

## Current State

The current project is a local prototype. It does not yet handle real private marketing data, multi-user access, authentication, or production deployment.

The current CSV upload workflow parses files in memory and does not persist uploaded data to disk. A production version should add authentication, explicit storage controls, audit logging, and retention policies before accepting private company data.

## Data Security Principles

For real company data, the project should follow these principles:

- No secrets in notebooks, code, or committed files.
- Use environment variables or a secrets manager.
- Validate all imported datasets before modeling.
- Avoid user-level attribution data unless there is a clear consent and privacy basis.
- Prefer aggregated weekly or geo-level data for MMM.
- Keep audit logs for model runs, exports, and scenario recommendations.

## Application Security Roadmap

A design demonstration of the governance core now exists in
`marketing_effectiveness_lab.access` (see `docs/phase-43-access-governance.md`): a
role-based permission matrix, an approval workflow with separation of duties, and an
append-only, hash-chained (tamper-evident) audit log, with a runnable demonstration in
`scripts/governance_demo.py`. This covers **authorization and audit**; **authentication**
(identity) and durable storage are still outstanding.

Future production versions should include:

- Authentication through SSO, OIDC, SAML, Auth0, Okta, or Microsoft Entra. **(outstanding)**
- Role-based access control. **(demonstrated in `access`)**
- Tenant isolation if used by multiple brands or clients. **(outstanding)**
- Row-level security in Postgres where applicable. **(outstanding)**
- Encrypted data at rest and in transit. **(outstanding)**
- Least-privilege warehouse/service credentials. **(outstanding)**
- Structured audit logs. **(demonstrated in `access` - hash-chained)**
- Approval workflow with separation of duties. **(demonstrated in `access`)**

## Engineering Roadmap

Recommended production engineering steps:

- Add CI for tests, linting, and type checks.
- Add dependency scanning.
- Add container scanning if deployed with Docker.
- Add SBOM generation.
- Add signed build provenance for production releases.
- Add model run tracking and artifact storage.
- Add data versioning for reproducibility.

## Modeling Governance Roadmap

For real decision-making, add:

- Model cards
- Experiment calibration notes
- Holdout performance reporting
- Prior assumptions
- Sensitivity analysis
- Business caveats
- Clear approval workflow for budget recommendations

## Recommended Standards To Align With

- OWASP ASVS
- OWASP API Security Top 10
- NIST Secure Software Development Framework
- SLSA supply-chain security guidance
- OpenSSF security scorecard practices
