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
uv run --group dev mypy
uv run streamlit run app/streamlit_app.py --server.port 8501 --server.headless true
```

### Metric sensitivity: does the suite notice when the maths stops?

A green suite is not evidence that anything is computed. Freeze a function so it returns a
constant of the right shape and dtype, and every assertion about shapes, column names, row
counts and `> 0` ranges still passes.

This repo failed that check. Four functions were completely undetectable — freezing any of
`analytics.summarize_kpis`, `analytics.channel_summary`, `analytics.promotion_summary` or
`uncertainty.simulate_mmm_uncertainty` produced **zero** red tests. `test_dashboard_metrics_are_computed`
asserted `revenue > 0`, `spend > 0` and `roas > 0`, all true of a constant `1.0`;
`test_simulate_mmm_uncertainty_returns_intervals` asserted `lower <= upper`, also true of a
constant. Across the whole suite, 20 of 139 tests noticed a fully frozen model; 119 did not.

Two things guard it now:

- [`tests/test_metric_sensitivity.py`](tests/test_metric_sensitivity.py) — a test per
  metric-bearing path, each written so a constant or scrambled output makes it red. Either an
  **oracle** (recompute the metric independently and require equality) or a **sensitivity** check
  (perturb an input, require the output to move).
- [`scripts/sabotage_sweep.py`](scripts/sabotage_sweep.py) — the audit itself, so the measurement
  is repeatable rather than a one-off claim:

  ```powershell
  uv run python scripts/sabotage_sweep.py
  ```

  It freezes **one function at a time** and reports per function, then exits non-zero if any
  function survived undetected. Per function matters: an earlier version froze three functions
  together and reported a single "3 detected", which hid the fact that `promotion_summary` was
  still completely blind. **A function that detects nothing is a finding, not a pass.**

If you add a function that produces a number anyone would quote, add it to the sweep's target list,
add a test to `test_metric_sensitivity.py`, and prove it bites:

```powershell
uv run python scripts/sabotage_sweep.py --target analytics.summarize_kpis
```

A test that passes under sabotage is not testing the thing you think it is.

One trap worth knowing: consumers import by value (`from ...mmm import hill_saturation`), so
patching only the defining module leaves those consumers running the real code. The sweep rebinds
every alias across the package for this reason — if you write your own injection by hand, do the
same, or you will credit coverage that does not exist.

### Type checking

The package ships a `py.typed` marker and a non-strict mypy configuration scoped to `src/`
(`[tool.mypy]` in `pyproject.toml`). CI runs ruff and pytest but **does not gate on mypy**, because
mypy does not currently pass. That is deliberate and recorded rather than hidden:

- **Known baseline: 36 errors across 6 files** — `reporting.py` (14), `customer.py` (11),
  `access.py` (4), `calibration.py` (3), `budget.py` (2), `data/customer_generator.py` (2).
- They are all the same idiom. Run manifests, CRM experiment artifacts and stakeholder payloads are
  genuinely heterogeneous, so they are typed `dict[str, object]`; values read back out are then
  passed straight to `int()` or `float()` without narrowing. The annotation is honest and the code
  is correct — mypy is right that the narrowing is missing.
- **No real defects were found.** All 36 are annotation precision, not bugs.

Clearing them means adding narrowing helpers at roughly 36 call sites. That is a reasonable
contribution, and the CI gate should be added in the same change rather than before it — a
configured checker that nothing runs is worse than no checker. Do not clear them by disabling error
codes.

## Pull request standard

Say what the change improves, which data contracts or workflows it touches, and whether the
tests or validation scripts exercise it. Note any tests you added or updated. If the change
makes a new claim, say how it can be verified from the repo.
