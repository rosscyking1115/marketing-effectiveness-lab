# Production and Security Roadmap

## Current State

The current project is a local prototype. It does not yet handle real private marketing data, multi-user access, authentication, or production deployment.

## Data Security Principles

For real company data, the project should follow these principles:

- No secrets in notebooks, code, or committed files.
- Use environment variables or a secrets manager.
- Validate all imported datasets before modeling.
- Avoid user-level attribution data unless there is a clear consent and privacy basis.
- Prefer aggregated weekly or geo-level data for MMM.
- Keep audit logs for model runs, exports, and scenario recommendations.

## Application Security Roadmap

Future production versions should include:

- Authentication through SSO, OIDC, SAML, Auth0, Okta, or Microsoft Entra.
- Role-based access control.
- Tenant isolation if used by multiple brands or clients.
- Row-level security in Postgres where applicable.
- Encrypted data at rest and in transit.
- Least-privilege warehouse/service credentials.
- Structured audit logs.

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

