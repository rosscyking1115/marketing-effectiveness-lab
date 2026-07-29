# Phase 15: Constrained Budget Optimization

## Objective

Move the planner from manual scenario comparison toward allocation recommendation.

This phase adds a transparent optimizer that recommends a weekly channel allocation under business constraints.

## What Was Added

The budget module now supports constrained allocation optimization across channels.

The optimizer can target:

- Contribution revenue.
- Profit after media cost.

It also supports:

- Fixed total weekly budget.
- Minimum channel share constraints.
- Maximum channel share constraints.
- Channel-level diagnostic output.
- Comparison against current-mix allocation at the same total budget.

## Dashboard Behavior

The Budget Scenario Planner now includes an `Optimized allocation` profile.

When selected, the analyst can choose:

- Optimization objective.
- Minimum channel share.
- Maximum channel share.

The dashboard then shows:

- Proposed optimized spend by channel.
- Scenario impact on contribution and profit.
- Optimization diagnostics showing objective lift and constraint status.

## Why This Matters

Commercial teams rarely ask only what happened. They ask what to do next.

This phase turns MMM outputs into an allocation recommendation while keeping the method explainable. It is useful for portfolio positioning because it connects:

- MMM response curves.
- Profit-aware planning.
- Business constraints.
- Decision support.

## Method Guardrails

The current optimizer uses deterministic greedy marginal response steps.

It is transparent and dependency-light, but it is not a global nonlinear optimizer. It does not yet account for:

- Posterior uncertainty in response curves.
- Category margin mix.
- Inventory constraints.
- Channel operational constraints beyond min/max shares.
- Brand or long-term carryover objectives.

## Future Product Path

A stronger production version should add:

- Posterior-aware robust optimization.
- Scenario risk metrics.
- Channel-specific minimums and maximums.
- Inventory and margin constraints.
- Approval workflow for recommended budget changes.
- Exportable media plan recommendations.

## Phase 15 Done Criteria

Phase 15 is complete when:

- Optimizer utilities exist in reusable package code.
- Optimized allocation preserves total budget.
- Min/max channel share constraints are validated and enforced.
- Dashboard exposes optimization objective and constraint controls.
- Tests cover optimizer behavior and validation.
