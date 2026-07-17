# Reconciling MMM with experiments

This is the loop the rest of the project builds towards: the MMM says one thing, the experiment
says another, and something has to decide what you actually believe.

The [validation study](validation.md) showed the observational MMM inflating channel ROI by
roughly 2–3×, because media spend is confounded with seasonal demand. An MMM cannot fix that on
its own. It is an identification problem, not a tuning problem. What fixes it is an incrementality
experiment: a geo holdout or conversion-lift test creates an unconfounded contrast that measures a
channel's true lift. The [calibration layer](../src/marketing_effectiveness_lab/calibration.py)
then pulls the biased MMM towards that evidence.

Reproduce with:

```powershell
uv run --group viz python scripts/reconcile_mmm_experiments.py
```

## The demonstration

Because the demo data is generated from known parameters, the experiment can be simulated
honestly: each test measures the true incremental revenue the generating process produced over an
8-week window, plus about 5% measurement error, which is roughly what a well-run test recovers.
Applying the engine's calibration to the observational MMM then gives three numbers per channel:
the true ROI, the observational MMM ROI, and the experiment-calibrated ROI.

![MMM and experiment reconciliation](assets/validation/mmm-experiment-reconciliation.png)

| Channel | True ROI | Observational MMM | Experiment-calibrated |
| --- | --- | --- | --- |
| Paid search | 3.66× | 6.68× | 3.66× |
| Paid social | 2.86× | 8.59× | 2.90× |
| Display | 2.70× | 10.37× | 2.67× |
| Influencer | 3.64× | 0.95× | 1.91× (clipped) |

Across the channels an experiment covers, mean absolute ROI error falls from 4.78× to 0.45×, about
91% closer to the truth. The reconciled estimate is one you could act on. The raw observational
estimate would have driven heavy over-investment in display and paid social.

## Where it doesn't fully work

Influencer only partly corrects. The MMM had under-attributed it badly (0.95× against a true
3.64×), and the calibration factor is clipped to `[0.25, 2.0]` so that a single experiment cannot
swing an estimate arbitrarily far. The clip protects against noisy tests, at the cost of not fully
rescuing a channel the model got badly wrong. That trade is deliberate, and worth stating rather
than hiding.

Affiliates and email have no experiment here, so they keep their MMM estimate, which the model had
collapsed towards zero. You only get causal correction where you actually ran a test, which is
also true of a real measurement programme.

Evidence is governed: only approved tests feed calibration, and each is scored on duration,
precision, and metadata completeness before it can move a number. [`methodology.md`](methodology.md)
§7 has the detail.
