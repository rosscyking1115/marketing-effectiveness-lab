# Model card — MMM foundation model

A model card ([Mitchell et al., 2019](https://arxiv.org/abs/1810.03993)) for the marketing mix
model at the centre of this reference implementation. It states, in one place, what the model is
for, how well it works, and — most importantly — when *not* to trust it.

## Model details

- **Model:** Marketing mix model (MMM) estimating weekly revenue as a function of media spend and
  controls. Geometric adstock + Hill saturation on media, ordinary least squares attribution, with
  a conjugate Bayesian layer for uncertainty and an experiment-calibration layer for causal
  correction.
- **Implementation:** `marketing_effectiveness_lab.mmm`, `.uncertainty`, `.bayesian`,
  `.calibration`, `.budget`. Python 3.11+, statsmodels / NumPy / pandas.
- **Version / license:** tracks the repository; Apache-2.0.
- **Owner:** Cheng-Yuan King. This is a **portfolio / reference implementation**, not a product.
- **Methodology:** documented in [`methodology.md`](methodology.md).

## Intended use

- **Primary use:** demonstrating and teaching end-to-end marketing-effectiveness measurement —
  channel contribution, ROI, diminishing returns, uncertainty, and experiment-calibrated budget
  planning — on aggregated weekly data.
- **Intended users:** data scientists and analysts reviewing the code as a reference, or extending
  it for their own learning.
- **Out-of-scope uses:** production budget decisions on confidential company data; any setting
  requiring authentication, governed storage, or audited access (see
  [`production-security-roadmap.md`](production-security-roadmap.md)); high-stakes allocation where
  a specialist tool (Meridian, Robyn, PyMC-Marketing) is warranted.

## Factors

- **Channels:** paid search, paid social, display, affiliates, email, influencer.
- **Controls:** linear + quadratic trend, promotion depth and flag, holiday flag, season, log
  organic search sessions, consumer confidence, inflation.
- **Grain / market:** weekly, UK, GBP, ~3 years of history.
- **Known sensitivity:** channels whose spend is strongly correlated with seasonal demand are
  harder to identify (see Limitations).

## Metrics

Measured on the deterministic demo dataset (seed 42), reproducible via the `scripts/validate_*`
and `scripts/rolling_origin_cv.py` scripts.

| Metric | Value | Source |
| --- | --- | --- |
| Holdout MAPE (26-week) | ~5% | [`methodology.md`](methodology.md) §4 |
| Rolling-origin MAPE (5 folds) | 4.3% mean, 0.9% std | [`cross-validation.md`](cross-validation.md) |
| Posterior-predictive coverage (nominal 90%) | ~81% | [`validation.md`](validation.md) |
| True ROI inside 90% interval | 6 / 6 channels | [`validation.md`](validation.md) |
| ROI bias, observational → calibrated | 4.78× → 0.45× error (91% closer) | [`reconciliation.md`](reconciliation.md) |

## Quantitative analyses

- **Parameter recovery & calibration** — [`validation.md`](validation.md): the model recovers the
  known data-generating ROI within its intervals, and those intervals are calibrated against the
  diagonal rather than asserted.
- **MMM ↔ experiment reconciliation** — [`reconciliation.md`](reconciliation.md): observational ROI
  is inflated ~2–3× by confounding; simulated geo-lift experiments plus the calibration layer
  correct it toward truth.
- **Rolling-origin cross-validation** — [`cross-validation.md`](cross-validation.md): out-of-sample
  accuracy is stable across five distinct quarters, including the Q4 peak.

## Ethical considerations & caveats

- The demo dataset is **synthetic** and clearly labelled; it is not real brand performance and must
  not be presented as such. Ground-truth parameters exist only because the data is generated.
- MMM informs, but does not replace, human judgment on budget decisions. Recommendations pass
  through readiness gates (`governance.py`) and carry explicit caveats.
- No personal data is used in the MMM path; the CRM modules operate on aggregated cohort data.

## Limitations — when not to trust it

- **Observational bias.** Point estimates are confounded where media spend correlates with demand
  drivers; per-channel ROI can be inflated ~2–3× without experimental calibration. Trust the
  *calibrated* estimate, or the interval, over the raw point estimate.
- **Fixed transform parameters.** The Bayesian layer is a posterior over the *fixed*
  adstock/saturation design; it does not sample those parameters, so it understates transform
  uncertainty (mild tail under-coverage).
- **No geo/hierarchical structure.** Single national time series; no pooling across markets.
- **Single dataset / seed** for the quantitative results. Broader seeds and datasets are on the
  [roadmap](product-roadmap.md).
- **Not production-hardened.** No authentication, governed storage, or audit for confidential data.

## Recommendations

Use it to *understand* how MMM, incrementality, and budget optimization fit together, and as a
starting point to extend. For production decisions on real, confidential data, pair it with a
specialist MMM tool and a real incrementality-testing program — the reconciliation study shows why
the experiments matter as much as the model.
