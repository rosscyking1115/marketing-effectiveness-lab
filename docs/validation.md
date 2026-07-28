# Validation: parameter recovery and uncertainty calibration

The demo dataset is generated from known adstock, saturation, and effect parameters (see
[`data/generator.py`](../src/marketing_effectiveness_lab/data/generator.py)), which makes two
questions answerable that real marketing data cannot answer at all:

1. Does the estimator recover the truth? (parameter recovery)
2. Is the uncertainty honest? (interval calibration)

The generator uses the same geometric adstock and Hill saturation (slope 1.35) as the model, and
its per-channel `decay` and `half_saturation` match the model defaults, so the fitted coefficient
on `{channel}_mmm` is directly comparable to the true generating `effect`.

That last point cuts both ways. Sections 1 and 2 hold the transform parameters at their true
values in order to isolate the effect and ROI question, which means neither of them tests whether
those transforms could have been found from the data. Section 3 asks that separately, and the
answer is no.

Two scripts reproduce everything below:

```powershell
uv run --group viz python scripts/validate_recovery.py
uv run python scripts/validate_transform_recovery.py
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

## 3. Are the adstock and saturation parameters recoverable at all?

Sections 1 and 2 hand the model the true `decay` and `half_saturation`, because
`DEFAULT_MEDIA_PARAMETERS` in [`mmm.py`](../src/marketing_effectiveness_lab/mmm.py) equals the
generating `media_specs`. So this section removes that help and asks whether the calibration search
could have found them. `scripts/validate_transform_recovery.py` runs the same time-aware search as
`calibrate_mmm_parameters()`, with two changes that matter:

- the half-saturation grid is an absolute lattice, £20k to £200k in £20k steps, rather than
  multipliers around the true value, so the truth is not sitting at the centre of the grid;
- the search starts from a neutral seed (decay 0.35, half-saturation £100k for every channel)
  instead of from the generating values.

The truth is read from `data/demo/ground_truth_metadata.json` — a file the generator has always
written and nothing had ever read — with a guard that fails the run if it has drifted from the
generator. That directory is git-ignored, so on a fresh clone the study falls back to the
in-process ground truth and says so.

| Channel | True decay | Recovered | True half-sat | Recovered | Half-sat error |
| --- | --- | --- | --- | --- | --- |
| Paid search | 0.25 | 0.65 | £92k | £200k | +117% |
| Paid social | 0.45 | 0.75 | £130k | £200k | +54% |
| Display | 0.55 | 0.65 | £72k | £200k | +178% |
| Affiliates | 0.15 | 0.75 | £45k | £20k | −56% |
| Email | 0.10 | 0.75 | £18k | £80k | +344% |
| Influencer | 0.60 | 0.55 | £65k | £200k | +208% |

Recovery fails. Mean absolute decay error is 0.35 on a grid spanning 0.05 to 0.75, which is about
half the range and no better than guessing; 1 of 6 channels lands on the grid point nearest its
true decay, and 0 of 6 on the nearest half-saturation. Four channels are pinned at the top of the
half-saturation grid.

The reason is not a bad search. It is that the objective is flat. Across all 80 grid points per
channel, validation MAPE moves between 3.09% and 3.60%, and within a channel the worst candidate is
at most 7.4% worse than the best in relative terms — a few hundredths of a percentage point of
MAPE. The data cannot distinguish the candidates, so the argmin is picking noise. The pinning at
£200k is the visible symptom: a large half-saturation makes the Hill curve nearly linear over the
observed spend range, and OLS then absorbs the difference into the coefficient, leaving the fit
essentially unchanged.

### What does knowing the true transforms actually buy?

A flat objective cuts both ways, so the caveat is worth measuring rather than asserting. The same
model, refit under three parameter sets:

| Transform parameters | Holdout MAPE | Holdout RMSE | Train R² | Mean channel ROI |
| --- | --- | --- | --- | --- |
| Generator truth (repo default) | 5.11% | £276,256 | 0.896 | 4.43× |
| Neutral (decay 0.35, half-sat £100k) | 4.98% | £270,508 | 0.893 | 3.84× |
| Independent search result | 6.65% | £332,765 | 0.891 | 3.81× |

Knowing the truth buys **nothing** on accuracy. Deliberately wrong, uniform parameters fit the
holdout marginally *better* (4.98% against 5.11%), which is the flat objective showing up in the
headline metric: over the observed spend range, adstock and saturation choices are close to
interchangeable once OLS rescales the coefficient. So the reported holdout accuracy in this repo is
not propped up by the free gift — it would survive the parameters being wrong.

What the gift does move is **ROI**, by about 13% (4.43× against 3.84×). That is the number to treat
as conditional, and it is the number the repo already tells you not to trust on its own: section 2
puts the ROI point estimates 2–3× above truth from confounding, and
[reconciliation](reconciliation.md) is the machinery for pulling them back. The transform
assumption is a second, smaller source of the same kind of error.

The defaults are left at the generating values, since changing them would move accuracy by 0.13
percentage points while breaking the premise of sections 1 and 2 — but the conditionality is
reported here rather than left implicit.

Three things follow, and they are the point of running this:

1. The tuned parameters that `calibrate_mmm_parameters()` reports are not identified by the data.
   They are legible and cheap, not estimates anyone should quote.
2. The defaults are correct because they were copied from the generator, not because the data
   revealed them — but per the table above, that is worth ~0.13 percentage points of holdout MAPE
   and about 13% of the ROI estimate. The accuracy claims stand without it; the ROI claims lean on
   it a little, on top of the much larger confounding bias in section 2.
3. Sections 1 and 2 remain valid on their own terms — recovery of effect and ROI *conditional on
   correct transforms* — but that condition is doing real work, and on real data nothing supplies
   it. Informative priors, pooling across channels, or experiments are what would.

## Limitations

- One dataset, one seed. Rolling-origin cross-validation across more holdout windows and seeds is
  the natural next step (see the [roadmap](product-roadmap.md)).
- The Bayesian layer is a posterior over the fixed transformed design. It does not sample the
  adstock and saturation parameters, so it understates transform uncertainty, which shows up as
  the mild tail under-coverage above. Section 3 is the direct measurement of how much that layer
  is assuming.
- Recovery is assessed on ROI and the media coefficient. The control block is not scored.
- The Hill slope is fixed at 1.35 in both the generator and the model, so section 3 does not test
  it. Only decay and half-saturation are searched.
- Section 3 scores a grid search by validation MAPE. A different objective (in-sample likelihood,
  a joint rather than per-channel search, or a Bayesian treatment that samples the transforms)
  might identify more. The finding is that *this* search cannot, and that the fit surface it
  searches is nearly flat.
