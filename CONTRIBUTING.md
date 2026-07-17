# Contributing

Marketing Effectiveness Lab is an open, Apache-2.0 reference implementation for marketing
measurement: MMM, incrementality, and budget optimisation. Contributions are welcome if they
make the methodology deeper or better validated, the code clearer, or the documentation easier
to learn from. It is a reference project rather than a product, so there is no pricing or
packaging work to do here.

## Principles

- Be honest about what is demo logic and what has been validated against ground truth.
- Prefer transparent methods that can be inspected over black-box claims.
- Validate input data before modelling or exporting decisions.
- Keep the methodology legible. Document assumptions next to the code that implements them.
- Don't add tooling unless a real problem here justifies it. Minimal dependencies are a
  feature.

## Good first contributions

- Add validation checks for uploaded marketing, CRM, or experiment data.
- Improve test coverage around connector diagnostics and CRM experiment workflows.
- Add examples showing how a real aggregated dataset maps into the documented contracts.
- Improve the methodology, validation, or data-contract documentation.
- Pull duplicated Streamlit presentation logic into reusable view helpers.

## Deeper extensions

These follow the [roadmap](docs/product-roadmap.md), and are the changes that would most
strengthen the reference:

- A fuller Bayesian MMM sampler that treats adstock and saturation parameters as random, with
  posterior predictive checks. The current layer is a posterior over the fixed design matrix.
- Richer geo-lift designs and clearer reconciliation between MMM and experiments (see
  [`docs/reconciliation.md`](docs/reconciliation.md)).
- More validation: additional rolling-origin folds, multiple seeds and datasets, and prior
  sensitivity analysis (see [`docs/validation.md`](docs/validation.md)).
- Identifiability diagnostics for collinearity between channels and controls.
- Engineering quality: type checking, wider coverage on the modelling paths, reproducibility.

## Local development

Install dependencies with [`uv`](https://docs.astral.sh/uv/), then:

```powershell
uv run --group dev ruff check .
uv run --group dev pytest
uv run streamlit run app/streamlit_app.py --server.port 8501 --server.headless true
```

## Pull request standard

Say what the change improves, which data contracts or workflows it touches, and whether the
tests or validation scripts exercise it. Note any tests you added or updated. If the change
makes a new claim, say how it can be verified from the repo.
