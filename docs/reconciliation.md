# MMM ↔ experiment reconciliation

This is the core causal-measurement loop, and the pay-off of the whole project: **MMM says X,
the experiment says Y, here is the reconciled estimate.**

The [validation study](validation.md) showed that the observational MMM inflates channel ROI
~2–3× because media spend is confounded with seasonal demand. An MMM alone cannot fix this —
it is an identification problem, not a tuning problem. What fixes it is an **incrementality
experiment**: a geo holdout or conversion-lift test creates an unconfounded causal contrast that
measures a channel's *true* lift. The engine's [calibration layer](../src/marketing_effectiveness_lab/calibration.py)
then reconciles the biased MMM toward that evidence.

Reproduce with:

```powershell
uv run --group viz python scripts/reconcile_mmm_experiments.py
```

## The demonstration

Because the demo data is generated from known parameters, we can simulate an **honest** geo-lift:
each experiment measures the true incremental revenue the generating process produced over an
8-week window (plus realistic ±5% measurement error), exactly what a well-run test would recover.
We then apply the engine's calibration to the observational MMM and compare three quantities per
channel — the **true** ROI, the **observational MMM** ROI, and the **experiment-calibrated** ROI.

![MMM–experiment reconciliation](assets/validation/mmm-experiment-reconciliation.png)

| Channel | True ROI | Observational MMM | Experiment-calibrated |
| --- | --- | --- | --- |
| Paid search | 3.66× | 6.68× | **3.66×** |
| Paid social | 2.86× | 8.59× | **2.90×** |
| Display | 2.70× | 10.37× | **2.67×** |
| Influencer | 3.64× | 0.95× | **1.91×** (clipped) |

Across the experiment-covered channels, the mean absolute ROI error falls from **4.78× to 0.45×
— 91% closer to the truth.** The reconciled estimate is one a decision-maker can actually act on;
the raw observational estimate would have driven large over-investment in display and paid social.

## Honest nuances

- **Influencer only partly corrects.** The MMM badly *under*-attributed it (0.95× vs a true
  3.64×), and the calibration factor is deliberately clipped to `[0.25, 2.0]` so a single
  experiment cannot swing an estimate arbitrarily far. The clip protects against noisy tests at
  the cost of not fully rescuing a severely mis-estimated channel — a worthwhile guardrail, stated
  rather than hidden.
- **Uncovered channels stay put.** Affiliates and email have no experiment here, so they retain
  their MMM estimate (which the model had collapsed toward zero). You only get causal correction
  where you actually ran a test — which is exactly how a real measurement program works.
- **Evidence is governed.** Only tests marked approved feed calibration, and each is quality-scored
  on duration, precision, and metadata before it can move a number (see
  [`methodology.md`](methodology.md) §7).

## Why this matters for the portfolio

Anyone can fit an MMM. The differentiated skill — and the thing modern tools like Google Meridian
are built around — is knowing that observational attribution is biased, quantifying that bias
against ground truth, and reconciling it with experimental evidence. This study demonstrates the
full loop end to end, with the size of the correction measured, not asserted.
