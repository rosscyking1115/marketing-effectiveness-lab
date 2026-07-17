# Model card: MMM foundation model

A model card, in the sense of [Mitchell et al. (2019)](https://arxiv.org/abs/1810.03993), for the
marketing mix model at the centre of this reference implementation. It states what the model is
for, how well it works, and when not to trust it.

## Model details

The model estimates weekly revenue from media spend and controls: geometric adstock and Hill
saturation on media, ordinary least squares attribution, a conjugate Bayesian layer for
uncertainty, and an experiment-calibration layer for causal correction. It lives in
`marketing_effectiveness_lab.mmm`, `.uncertainty`, `.bayesian`, `.calibration` and `.budget`, and
runs on Python 3.11+ with statsmodels, NumPy and pandas.

Versioning tracks the repository, the licence is Apache-2.0, and the author is Cheng-Yuan King.
This is a reference implementation rather than a product.
[`methodology.md`](methodology.md) documents the approach.

## Intended use

It exists to demonstrate and teach end-to-end marketing-effectiveness measurement on aggregated
weekly data: channel contribution, ROI, diminishing returns, uncertainty, and
experiment-calibrated budget planning. The readers it is written for are data scientists and
analysts reading the code as a reference, or extending it for their own learning.

It is not for production budget decisions on confidential company data, nor for any setting
needing authentication, governed storage, or audited access (see
[`production-security-roadmap.md`](production-security-roadmap.md)). For high-stakes allocation,
use a specialist tool: Meridian, Robyn, or PyMC-Marketing.

## Factors

Channels are paid search, paid social, display, affiliates, email and influencer. Controls are a
linear and quadratic trend, promotion depth and flag, holiday flag, season, log organic search
sessions, consumer confidence, and inflation. The grain is weekly, the market is the UK, the
currency is GBP, and the history is about 3 years.

Channels whose spend correlates strongly with seasonal demand are harder to identify. The
Limitations section explains why.

## Metrics

Measured on the deterministic demo dataset (seed 42) and reproducible via the `scripts/validate_*`
and `scripts/rolling_origin_cv.py` scripts.

| Metric | Value | Source |
| --- | --- | --- |
| Holdout MAPE (26-week) | ~5% | [`methodology.md`](methodology.md) §4 |
| Rolling-origin MAPE (5 folds) | 4.3% mean, 0.9% std | [`cross-validation.md`](cross-validation.md) |
| Posterior-predictive coverage (nominal 90%) | ~81% | [`validation.md`](validation.md) |
| True ROI inside 90% interval | 6 of 6 channels | [`validation.md`](validation.md) |
| ROI error, observational to calibrated | 4.78× to 0.45× (91% closer) | [`reconciliation.md`](reconciliation.md) |

## Quantitative analyses

[`validation.md`](validation.md) covers parameter recovery and calibration: the model recovers the
known data-generating ROI within its intervals, and those intervals are measured against the
diagonal rather than asserted. [`reconciliation.md`](reconciliation.md) covers the MMM-experiment
loop: observational ROI is inflated 2–3× by confounding, and simulated geo-lift tests plus the
calibration layer correct it towards truth. [`cross-validation.md`](cross-validation.md) covers
rolling-origin backtesting, where out-of-sample accuracy stays stable across five quarters
including the Q4 peak.

## Ethical considerations

The demo dataset is synthetic and labelled as such. It is not real brand performance and must not
be presented that way. Ground-truth parameters only exist because the data is generated.

MMM informs budget decisions; it does not replace judgement about them. Recommendations pass
through readiness gates in `governance.py` and carry their caveats. No personal data is used in
the MMM path, and the CRM modules work on aggregated cohort data.

## Limitations: when not to trust it

- Point estimates are confounded wherever media spend correlates with demand drivers, and
  per-channel ROI can be inflated 2–3× without experimental calibration. Trust the calibrated
  estimate, or the interval, ahead of the raw point estimate.
- The Bayesian layer is a posterior over the fixed adstock and saturation design. It does not
  sample those parameters, so it understates transform uncertainty, which shows as mild tail
  under-coverage.
- There is no geo or hierarchical structure. It is a single national time series with no pooling
  across markets.
- The quantitative results come from one dataset and one seed. Broader seeds and datasets are on
  the [roadmap](product-roadmap.md).
- It is not production-hardened: no authentication, governed storage, or audit for confidential
  data.

## Recommendations

Use it to understand how MMM, incrementality, and budget optimisation fit together, and as a
starting point to extend. For production decisions on real confidential data, pair it with a
specialist MMM tool and a real incrementality-testing programme. The reconciliation study is the
argument for why the experiments matter as much as the model.
