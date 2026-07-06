# Methodology & Validation

This document is the technical core of the project. It explains **how** marketing effect is
estimated and **how each step is validated**, and it points at the exact code that implements
each idea. It is written for a data-science reviewer: every modeling choice, and its
limitation, is stated plainly.

The pipeline is a marketing mix model (MMM): media spend is transformed for *carryover*
(adstock) and *diminishing returns* (saturation), a linear model attributes revenue across
media and controls, and the resulting contribution/ROI estimates are quantified with
uncertainty and reconciled against experiment (lift-test) evidence before they inform a
constrained budget allocation.

```
spend ──adstock──▶ carryover ──saturation──▶ response ──┐
                                                        ├─▶ OLS on media + controls ─▶ contribution / ROI
controls (trend, seasonality, promo, macro) ────────────┘        │
                                                                  ├─▶ coefficient Monte Carlo ─▶ intervals
                                                                  ├─▶ conjugate Bayesian layer ─▶ posterior + priors
                                                                  ├─▶ lift-test calibration ─▶ evidence-adjusted contribution
                                                                  └─▶ marginal budget optimizer ─▶ allocation
```

---

## 1. Adstock (carryover)

Media effect does not vanish the week it is spent; it decays. The engine uses **geometric
adstock**: each week accumulates a decayed fraction of the previous week's adstocked value.

```
adstock_t = spend_t + decay · adstock_{t-1},   decay ∈ [0, 1)
```

- Code: `geometric_adstock()` in [`src/marketing_effectiveness_lab/mmm.py`](../src/marketing_effectiveness_lab/mmm.py).
- Each channel has its own `adstock_decay`. Defaults encode a prior belief about media
  dynamics — e.g. email and affiliates decay fast (`0.10`–`0.15`, near-immediate response),
  paid social and influencer decay slowly (`0.45`–`0.60`, longer carryover).
- **Limitation:** this is single-parameter geometric adstock with no delay/peak (no lagged
  "hump"). A delayed-peak adstock (e.g. Weibull) is a natural extension.

## 2. Saturation (diminishing returns)

Doubling spend does not double revenue. The engine uses a **Hill saturation** curve on the
adstocked spend:

```
response = x^slope / (x^slope + half_saturation^slope)
```

- Code: `hill_saturation()` in [`mmm.py`](../src/marketing_effectiveness_lab/mmm.py).
- `half_saturation` is the spend at which a channel reaches half of its ceiling; `slope`
  controls how sharply returns bend. Output is in `[0, 1)`, so the fitted regression
  coefficient carries the revenue scale.
- This is what produces the **response curves** and the marginal-return logic the budget
  optimizer relies on.

## 3. The model: attribution across media and controls

Transformed media features (`{channel}_mmm`) plus a fixed control set are fit with **OLS**
(`statsmodels`) against weekly revenue.

- Code: `fit_mmm_foundation_model()` in [`mmm.py`](../src/marketing_effectiveness_lab/mmm.py).
- **Controls** (`CONTROL_FEATURES`): linear + quadratic `trend`, `promotion_depth_pct`,
  `promotion_flag`, `holiday_flag`, a single `season_spring_summer` dummy, log organic search
  sessions, consumer confidence, and inflation. These absorb baseline demand so media
  coefficients are not inflated by seasonality or promotions.
- **Identifiability note (in the code):** the two season dummies are exact complements, so
  only one is included — otherwise the design matrix is rank-deficient. This kind of explicit
  collinearity control is deliberately called out rather than hidden.
- **Contribution & ROI:** `_contribution_table()` multiplies each media coefficient (floored
  at zero — negative media effects are treated as zero, a standard MMM prior) by that
  channel's total transformed response; ROI = contribution ÷ spend.

## 4. Validation: time-aware holdout

Marketing data is a time series, so validation never shuffles rows.

- The last `holdout_weeks` (default **26**) are held out as a **contiguous** test set; the
  model is fit only on the earlier weeks (`fit_mmm_foundation_model`).
- Reported metrics (`_metrics()`): train R² / adjusted R², train MAPE, **holdout MAPE**,
  holdout RMSE. Holdout MAPE is the honest generalization signal — a strong in-sample R² with
  a weak holdout MAPE is exactly the overfit story this split is designed to expose.

## 5. Calibrating the transformation parameters

Adstock decay and saturation are not left at their defaults blindly — they are tuned with a
**nested, time-aware search** that never touches the final holdout.

- Code: `calibrate_mmm_parameters()` in [`mmm.py`](../src/marketing_effectiveness_lab/mmm.py).
- For each channel, a small grid — `decay ∈ {0.10, 0.30, 0.50, 0.70}` × `half_saturation`
  multiplier `∈ {0.70, 1.00, 1.30}` — is scored by **validation MAPE** on a further-nested
  validation window carved out *before* the 26-week test set. The parameter set with the
  lowest validation MAPE wins.
- This is a grid search, not a global optimizer, and it tunes one channel at a time; it is
  meant to be legible and cheap, not exhaustive.

## 6. Uncertainty

A point estimate without a confidence statement is not a recommendation. Two complementary
layers are provided.

**(a) Frequentist coefficient Monte Carlo** — `simulate_mmm_uncertainty()` in
[`uncertainty.py`](../src/marketing_effectiveness_lab/uncertainty.py). Draws coefficients from
the fitted OLS estimate and its covariance matrix (`multivariate_normal`, PSD-projected for
numerical safety), then propagates each draw to **contribution intervals** and **prediction
intervals** (default 90%). This answers: given estimation error, how uncertain is each
channel's contribution?

**(b) Conjugate Bayesian layer** — `fit_bayesian_mmm()` in
[`bayesian.py`](../src/marketing_effectiveness_lab/bayesian.py). A **Normal–Inverse-Gamma**
posterior over the *same* adstock/saturation design matrix, sampled analytically (no MCMC).
It returns posterior coefficient summaries (including `probability_positive`), contribution
intervals, and **posterior predictive** intervals on the holdout.

> **Honesty about scope (stated in the code's own docstring):** the Bayesian layer is a
> posterior over the *fixed* transformed design matrix. It is **not** a full Bayesian MMM that
> samples the adstock and saturation parameters themselves. That boundary is intentional and
> documented, not glossed over — and moving to a full sampler is the top methodology roadmap
> item.

**Priors** (`build_prior_table()`): media coefficient priors are centered on the OLS estimate
(floored at zero) with a *tighter* prior SD (`0.65×`), controls get a looser SD (`1.5×`) —
encoding more confidence that media effects are near their estimated magnitude and
non-negative. Media priors can be **shifted by experiment evidence** (next section).

**Validation of the intervals:** `_diagnostics()` reports **holdout coverage** — the fraction
of held-out weeks that actually fall inside the posterior predictive interval. Coverage near
the nominal width is evidence the uncertainty is calibrated, not decorative. The
[validation study](validation.md) measures this against the diagonal across nominal levels
(90% intervals cover ~81% of held-out weeks) and, because the demo data has known
data-generating parameters, checks whether the model **recovers the truth** — see
[`validation.md`](validation.md).

## 7. Incrementality / geo-lift calibration

MMM is observational; experiments are causal. The engine reconciles the two.

- Code: [`calibration.py`](../src/marketing_effectiveness_lab/calibration.py).
- Lift-test readouts (geo holdout, conversion lift, matched-market) are uploaded against a
  strict schema (`REQUIRED_LIFT_TEST_COLUMNS`) and validated (`validate_lift_tests`): channel
  names must be known, intervals must bracket the point estimate, values must be positive, etc.
- **Evidence quality scoring** (`assess_lift_test_evidence`): each test is scored 0–100 on
  duration, interval precision, metadata completeness, and how far its implied factor sits
  from the model — then tiered *Strong / Usable / Needs review* with human-readable flags
  ("Short test", "Wide interval", "Large MMM mismatch"). Only **approved** evidence feeds
  calibration.
- **Calibration factor** = observed lift ÷ model-implied lift, aggregated per channel and
  **clipped to `[0.25, 2.0]`** so a single noisy test cannot swing contribution wildly.
- The factor is applied three ways: to the contribution table
  (`apply_lift_calibration`), to the uncertainty intervals
  (`apply_lift_calibration_to_intervals`), and as a **prior mean shift** in the Bayesian layer
  (priors tagged `Experiment-informed`). This is the "MMM + incrementality" loop: an
  experiment doesn't just sit beside the model, it moves it.
- **Worked end to end** in [`reconciliation.md`](reconciliation.md): against known ground truth,
  calibration cuts the observational ROI bias by ~91%.

## 8. From estimates to a budget decision

- Code: [`budget.py`](../src/marketing_effectiveness_lab/budget.py).
- Weekly response uses the **steady-state** adstock level `spend / (1 − decay)` through the
  Hill curve, so the optimizer plans on sustained-spend response, not a single week's pulse
  (`response_for_weekly_spend`).
- `optimize_budget_allocation()` is a **greedy marginal allocator**: it seeds every channel at
  its minimum share, then repeatedly adds a small budget increment to whichever channel yields
  the highest **marginal** gain in the objective — `profit` (gross-margin-weighted contribution
  minus spend) or `contribution` — subject to per-channel `min_share` / `max_share` bounds.
  Because each channel's response is concave (Hill), chasing the marginal gain approximates the
  constrained optimum while respecting business guardrails.
- `governance.py` gates a recommendation on model fit, profit impact, spend movement, history
  length, and evidence before it is presented — the "is this ready to show a stakeholder?"
  check.

## 9. What this is, and is not

**Is:** a transparent, end-to-end, tested reference for MMM + incrementality + budget
optimization, with every transformation, prior, and validation step documented next to the
code that implements it.

**Is not:** a production Bayesian MMM sampler over carryover/saturation parameters, a
hierarchical/geo-level model, or a substitute for specialist tools (Google Meridian, Meta
Robyn, PyMC-Marketing) in high-stakes decisions. Those boundaries are deliberate and are the
subject of the [roadmap](product-roadmap.md).

## Reproduce it

```powershell
uv run python scripts/generate_demo_data.py        # deterministic demo data
uv run --group dev pytest                           # full test suite, incl. modeling paths
uv run streamlit run app/streamlit_app.py           # inspect every step interactively
```

Real public data (UCI Online Retail II) can be substituted via
`scripts/build_public_mmm_dataset.py` — see [`phase-44-real-connector-mmm.md`](phase-44-real-connector-mmm.md).
