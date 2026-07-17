# Validation: parameter recovery and uncertainty calibration

The demo dataset is generated from known adstock, saturation, and effect parameters (see
[`data/generator.py`](../src/marketing_effectiveness_lab/data/generator.py)), which makes two
questions answerable that real marketing data cannot answer at all:

1. Does the estimator recover the truth? (parameter recovery)
2. Is the uncertainty honest? (interval calibration)

The generator uses the same geometric adstock and Hill saturation (slope 1.35) as the model, and
its per-channel `decay` and `half_saturation` match the model defaults, so the fitted coefficient
on `{channel}_mmm` is directly comparable to the true generating `effect`.

One script reproduces everything below:

```powershell
uv run --group viz python scripts/validate_recovery.py
```

## A bug this study caught

Building the calibration check exposed a defect in the Bayesian layer, which is more or less what
a recovery harness is for.

The design matrix mixes columns on very different scales: saturated media features live in
`[0, 1)`, while `trend_squared` reaches the tens of thousands. Forming the Normal-Inverse-Gamma
posterior on that raw matrix meant inverting a near-singular `X'X`, with a condition number around
5×10¹². The `trend_squared` coefficient drifted about 100× off its OLS value (2558 against 26),
holdout predictions came out an order of magnitude too high, and interval coverage collapsed to
zero.

The fix in [`bayesian.py`](../src/marketing_effectiveness_lab/bayesian.py) whitens each column by
its L2 norm, solves the posterior in the well-conditioned basis (condition number around 2×10²),
and maps the draws back. It is an exact reparameterisation, so the prior semantics are unchanged.
Afterwards the posterior tracks OLS in the well-identified directions (`trend_squared` at 25.9
against 26.2) and holdout MAPE drops from roughly 1200% to about 5%. A regression test,
`test_bayesian_posterior_is_well_conditioned`, guards it.

## 1. Uncertainty calibration

For each nominal level, this measures the fraction of held-out weeks that fall inside the
posterior-predictive interval. Perfect calibration sits on the diagonal.

![Calibration coverage](assets/validation/calibration-coverage.png)

| Nominal | 50% | 60% | 70% | 80% | 90% | 95% |
| --- | --- | --- | --- | --- | --- | --- |
| Empirical holdout coverage | 50% | 50% | 65% | 77% | 81% | 81% |

The intervals sit close to nominal and slightly narrower: the 90% band covers about 81% of the 26
held-out weeks. The uncertainty is roughly right, with a mild tendency to overconfidence at the
tails. That is expected for a conjugate posterior over a fixed adstock and saturation design,
which ignores parameter uncertainty in the transforms themselves. The number is reported as it
came out, not tuned to land on 90%.

## 2. Parameter recovery

Each channel's true ROI, from the generating process, is plotted against the recovered posterior
mean with 90% credible intervals. Perfect recovery sits on the diagonal.

![Parameter recovery](assets/validation/parameter-recovery-roi.png)

All 6 of 6 true channel ROIs fall inside their 90% credible intervals, so the model knows what it
doesn't know: the intervals are wide and they cover the truth. The point estimates, though, are
inflated by roughly 2–3× (paid search 7.0× against a true 3.7×, paid social 8.4× against 2.9×,
display 10.4× against 2.7×), and the collinear channels, affiliates and email, are crushed towards
zero. Calibrated, in other words, but biased.

That is the identification problem at the heart of observational MMM rather than a coding error.
In the generating process, media spend is deliberately correlated with seasonal demand: spend
scales with the same seasonality and promotion schedule that drives baseline revenue. The model's
controls, a linear and quadratic trend plus a single binary season dummy, cannot fully absorb that
continuous seasonality, so the media coefficients soak up demand that seasonality actually caused.
Anyone trusting the point estimates would over-invest.

This is why the engine has an incrementality-calibration layer. A geo holdout or conversion-lift
experiment gives an unconfounded causal anchor, and the
[calibration](../src/marketing_effectiveness_lab/calibration.py) step reconciles the biased
observational estimate towards it. The [reconciliation study](reconciliation.md) closes that loop
and cuts the ROI bias measured here by about 91%. What recovery adds is the size of the bias the
experiments are there to remove.

## Limitations

- One dataset, one seed. Rolling-origin cross-validation across more holdout windows and seeds is
  the natural next step (see the [roadmap](product-roadmap.md)).
- The Bayesian layer is a posterior over the fixed transformed design. It does not sample the
  adstock and saturation parameters, so it understates transform uncertainty, which shows up as
  the mild tail under-coverage above.
- Recovery is assessed on ROI and the media coefficient. The control block is not scored.
