# Phase 5: Budget Scenario Planner

## Objective

Turn the MMM foundation outputs into a first decision-support workflow.

This phase adds a budget scenario planner that compares current weekly media spend with a proposed channel allocation.

## What The Planner Does

The planner uses the MMM foundation response curves to estimate:

- Current weekly media spend
- Proposed weekly media spend
- Estimated contribution change
- Scenario ROI
- Channel-level proposed ROI
- Channel-level incremental ROI where spend increases

Current weekly spend is estimated from the latest lookback window, defaulting to 13 weeks.

## Allocation Profiles

The dashboard supports three allocation modes:

- Current mix: preserves the existing channel mix while changing total budget.
- ROI-weighted tilt: shifts budget toward channels with stronger estimated ROI.
- Manual shares: lets the analyst set channel allocation shares directly.

## Why This Comes Before Full Optimization

A scenario planner is easier to trust than a black-box optimizer. It lets the analyst ask practical what-if questions:

- What if we increase budget by 10%?
- What if we keep total budget flat but tilt toward higher-ROI channels?
- Which channels appear saturated?
- Where does incremental ROI look weak?

This creates a useful bridge between MMM diagnostics and formal constrained optimization.

## Interpretation Guardrails

The planner is directional.

It does not yet include:

- Bayesian uncertainty
- Confidence or credible intervals
- Channel minimum/maximum constraints
- Campaign-level constraints
- Brand vs performance budget rules
- Experiment-calibrated incrementality
- Profit or margin optimization

The next step should be either calibrated Bayesian MMM or a formal constrained optimizer on top of uncertainty-aware response curves.

## Phase 5 Done Criteria

Phase 5 is complete when:

- Current weekly spend can be estimated by channel.
- Proposed allocations can be evaluated.
- ROI-weighted and manual allocation modes are available.
- The dashboard renders planner KPIs, charts, and channel table.
- Tests cover budget planner behavior.

