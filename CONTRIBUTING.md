# Contributing

Marketing Effectiveness Lab is an open, Apache-2.0 **reference implementation** for marketing
measurement — MMM, incrementality, and budget optimisation. Contributions are welcome that make
the methodology deeper or better-validated, the code clearer or more reliable, or the
documentation easier to learn from. It is a reference project, not a commercial product; there is
no pricing, packaging, or go-to-market to build.

## Principles

- Be honest about what is demo logic and what is validated against ground truth.
- Prefer transparent, inspectable methods over black-box claims.
- Validate input data before modelling or exporting decisions.
- Keep the methodology legible: document assumptions next to the code that implements them.
- Don't add tooling a real problem in this project doesn't justify — minimal dependencies are a
  feature.

## Good first contributions

- Add validation checks for uploaded marketing, CRM, or experiment data.
- Improve test coverage around connector diagnostics and CRM experiment workflows.
- Add examples that show how a real aggregated dataset maps into the documented contracts.
- Improve documentation for the methodology, validation, or data contracts.
- Refactor duplicated Streamlit presentation logic into reusable view helpers.

## Deeper extensions

These mirror the [roadmap](docs/product-roadmap.md) — the methodology and engineering directions
that would most strengthen the reference:

- A fuller Bayesian MMM sampler that treats adstock and saturation parameters as random, with
  posterior predictive checks (the current layer is a posterior over the fixed design matrix).
- Richer geo-lift / incrementality designs and clearer MMM ↔ experiment reconciliation
  (see [`docs/reconciliation.md`](docs/reconciliation.md)).
- Validation depth: more rolling-origin folds, multiple seeds/datasets, and prior sensitivity
  analysis (see [`docs/validation.md`](docs/validation.md)).
- Identifiability diagnostics for collinearity between channels and controls.
- Engineering quality: type checking, expanded coverage on modelling paths, and reproducibility.

## Local development

Install dependencies with [`uv`](https://docs.astral.sh/uv/), then:

```powershell
uv run --group dev ruff check .
uv run --group dev pytest
uv run streamlit run app/streamlit_app.py --server.port 8501 --server.headless true
```

## Pull request standard

Before opening a PR, include:

- What the change improves (methodology, correctness, clarity, or validation).
- Which data contracts or workflows are affected.
- Whether the change is demo-only or exercised by the tests / validation scripts.
- Tests added or updated.
- Any data-handling or honesty implications (e.g. new claims must be verifiable from the repo).
