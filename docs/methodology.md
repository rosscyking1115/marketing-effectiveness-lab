# Methodology and validation

This is the technical core of the project: how marketing effect is estimated, how each step is
validated, and where the code that does it lives. Every modelling choice has a limitation, and
both are stated here.

The pipeline is a marketing mix model. Media spend is transformed for carryover (adstock) and
diminishing returns (saturation), a linear model attributes revenue across media and controls,
and the resulting contribution and ROI estimates get uncertainty attached and are reconciled
against lift-test evidence before they inform a constrained budget allocation.

```
spend ──adstock──▶ carryover ──saturation──▶ response ──┐
                                                        ├─▶ OLS on media + controls ─▶ contribution / ROI
controls (trend, seasonality, promo, macro) ────────────┘        │
                                                                  ├─▶ coefficient Monte Carlo ─▶ intervals
                                                                  ├─▶ conjugate Bayesian layer ─▶ posterior + priors
                                                                  ├─▶ lift-test calibration ─▶ evidence-adjusted contribution
                                                                  └─▶ marginal budget optimiser ─▶ allocation
```

## 1. Adstock (carryover)

Media effect does not vanish the week it is spent. It decays. The engine uses geometric adstock,
where each week accumulates a decayed fraction of the previous week's adstocked value:

```
adstock_t = spend_t + decay · adstock_{t-1},   decay ∈ [0, 1)
```

`geometric_adstock()` in [`mmm.py`](../src/marketing_effectiveness_lab/mmm.py) implements it. Each
channel has its own `adstock_decay`, and the defaults encode a belief about media dynamics: email
and affiliates decay fast (`0.10`–`0.15`, near-immediate response), paid social and influencer
decay slowly (`0.45`–`0.60`, longer carryover).

The limitation is that this is single-parameter geometric adstock with no delay or peak, so no
lagged hump. A delayed-peak adstock such as Weibull is the natural extension.

## 2. Saturation (diminishing returns)

Doubling spend does not double revenue. The engine puts a Hill saturation curve on the adstocked
spend:

```
response = x^slope / (x^slope + half_saturation^slope)
```

`hill_saturation()` in [`mmm.py`](../src/marketing_effectiveness_lab/mmm.py) implements it.
`half_saturation` is the spend at which a channel reaches half its ceiling, and `slope` controls
how sharply returns bend. The output is in `[0, 1)`, so the fitted regression coefficient carries
the revenue scale. These curves are what the response plots show and what the budget optimiser's
marginal-return logic runs on.

## 3. The model: attribution across media and controls

Transformed media features (`{channel}_mmm`) and a fixed control set are fit with OLS
(`statsmodels`) against weekly revenue, in `fit_mmm_foundation_model()`.

The controls in `CONTROL_FEATURES` are a linear and quadratic `trend`, `promotion_depth_pct`,
`promotion_flag`, `holiday_flag`, a single `season_spring_summer` dummy, log organic search
sessions, consumer confidence, and inflation. They absorb baseline demand, so media coefficients
are not inflated by seasonality or promotions.

One identifiability detail is worth naming, and the code says so too: the two season dummies are
exact complements, so only one is included. Both would make the design matrix rank-deficient.

For contribution and ROI, `_contribution_table()` multiplies each media coefficient by that
channel's total transformed response, then divides by spend. Coefficients are floored at zero, so
negative media effects count as zero, which is a standard MMM prior.

## 4. Validation: time-aware holdout

Marketing data is a time series, so validation never shuffles rows. The last `holdout_weeks`
(default 26) are held out as a contiguous test set, and the model is fit only on the earlier
weeks.

`_metrics()` reports train R² and adjusted R², train MAPE, holdout MAPE, and holdout RMSE.
Holdout MAPE is the one that tells you about generalisation. A strong in-sample R² next to a weak
holdout MAPE is the overfit story this split exists to expose.

## 5. Calibrating the transformation parameters

Adstock decay and saturation are tuned rather than left at defaults, using a nested, time-aware
search that never touches the final holdout. `calibrate_mmm_parameters()` scores a small grid per
channel, `decay ∈ {0.10, 0.30, 0.50, 0.70}` against a `half_saturation` multiplier
`∈ {0.70, 1.00, 1.30}`, by validation MAPE on a further-nested window carved out before the
26-week test set. Lowest validation MAPE wins.

It is a grid search rather than a global optimiser, and it tunes one channel at a time. That keeps
it legible and cheap, not exhaustive.

## 6. Uncertainty

A point estimate without a confidence statement is not a recommendation. There are two layers.

The frequentist one is `simulate_mmm_uncertainty()` in
[`uncertainty.py`](../src/marketing_effectiveness_lab/uncertainty.py). It draws coefficients from
the fitted OLS estimate and its covariance matrix (`multivariate_normal`, PSD-projected for
numerical safety), then propagates each draw into contribution intervals and prediction intervals,
90% by default. It answers how uncertain each channel's contribution is given estimation error.

The Bayesian one is `fit_bayesian_mmm()` in
[`bayesian.py`](../src/marketing_effectiveness_lab/bayesian.py): a Normal-Inverse-Gamma posterior
over the same adstock and saturation design matrix, sampled analytically with no MCMC. It returns
posterior coefficient summaries including `probability_positive`, contribution intervals, and
posterior predictive intervals on the holdout.

Its scope is limited, and the code's own docstring says so: it is a posterior over the fixed
transformed design matrix, not a full Bayesian MMM that samples the adstock and saturation
parameters themselves. Moving to a full sampler is the top item on the methodology roadmap.

`build_prior_table()` centres media coefficient priors on the OLS estimate, floored at zero, with
a tighter prior SD (`0.65×`); controls get a looser SD (`1.5×`). That encodes more confidence that
media effects sit near their estimated magnitude and stay non-negative. Experiment evidence can
shift the media priors, which is the next section.

`_diagnostics()` reports holdout coverage, the fraction of held-out weeks falling inside the
posterior predictive interval. Coverage near the nominal width is what makes the uncertainty
worth reading. The [validation study](validation.md) measures it across nominal levels (90%
intervals cover about 81% of held-out weeks) and, because the demo data has known generating
parameters, checks whether the model recovers them.

## 7. Incrementality and geo-lift calibration

MMM is observational; experiments are causal. [`calibration.py`](../src/marketing_effectiveness_lab/calibration.py)
reconciles the two.

Lift-test readouts (geo holdout, conversion lift, matched-market) are uploaded against a strict
schema in `REQUIRED_LIFT_TEST_COLUMNS` and checked by `validate_lift_tests`: channel names must be
known, intervals must bracket the point estimate, values must be positive.

`assess_lift_test_evidence` then scores each test from 0 to 100 on duration, interval precision,
metadata completeness, and how far its implied factor sits from the model, and tiers it Strong,
Usable, or Needs review with readable flags such as "Short test", "Wide interval", or "Large MMM
mismatch". Only approved evidence feeds calibration.

The calibration factor is observed lift divided by model-implied lift, aggregated per channel and
clipped to `[0.25, 2.0]` so one noisy test cannot swing contribution wildly. It gets applied in
three places: the contribution table (`apply_lift_calibration`), the uncertainty intervals
(`apply_lift_calibration_to_intervals`), and as a prior mean shift in the Bayesian layer, where
those priors are tagged `Experiment-informed`. An experiment doesn't sit beside the model here; it
moves it.

[`reconciliation.md`](reconciliation.md) works this through end to end: against known ground
truth, calibration cuts the observational ROI bias by about 91%.

## 8. From estimates to a budget decision

[`budget.py`](../src/marketing_effectiveness_lab/budget.py) turns response curves into an
allocation. Weekly response uses the steady-state adstock level, `spend / (1 − decay)`, through
the Hill curve, so `response_for_weekly_spend` plans on sustained-spend response rather than a
single week's pulse.

`optimize_budget_allocation()` is a greedy marginal allocator. It seeds every channel at its
minimum share, then repeatedly adds a small budget increment to whichever channel gives the
highest marginal gain in the objective, either `profit` (gross-margin-weighted contribution minus
spend) or `contribution`, subject to per-channel `min_share` and `max_share` bounds. Each
channel's response is concave under Hill, so chasing the marginal gain approximates the
constrained optimum while respecting the business guardrails.

`governance.py` then gates a recommendation on model fit, profit impact, spend movement, history
length, and evidence. It is the "is this ready to show a stakeholder?" check.

## Scope

This is a transparent, tested reference for MMM, incrementality, and budget optimisation, with
every transformation, prior, and validation step documented next to the code that implements it.

It is not a production Bayesian MMM sampler over carryover and saturation parameters, a
hierarchical or geo-level model, or a substitute for Google Meridian, Meta Robyn, or
PyMC-Marketing on high-stakes decisions. Those boundaries are deliberate, and the
[roadmap](product-roadmap.md) covers them.

## Reproduce it

```powershell
uv run python scripts/generate_demo_data.py        # deterministic demo data
uv run --group dev pytest                           # full test suite, incl. modelling paths
uv run streamlit run app/streamlit_app.py           # inspect every step interactively
```

Real public data (UCI Online Retail II) can be substituted via
`scripts/build_public_mmm_dataset.py`. See [`phase-44-real-connector-mmm.md`](phase-44-real-connector-mmm.md).
