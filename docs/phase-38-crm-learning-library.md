# Phase 38 - CRM Experiment Learning Library

## Purpose

Phase 38 turns CRM experiment readouts into a reusable learning library. Instead of treating each readout as a one-off file, the dashboard now aggregates learnings by segment, channel, offer/action, decision outcome, and confidence.

## What changed

- Added a deterministic CRM experiment learning-library builder.
- Added learning rows for segment, dominant channel, offer/action, decision outcome, and confidence.
- Added learning status and recommended learning action fields.
- Added a learning-library summary and CSV export.
- Added a Streamlit learning-library table under the CRM portfolio planner.
- Added tests for learning dimensions, summary metrics, recommended actions, and CSV shape.

## Learning logic

The learning library is built from the portfolio readout package:

- Segment learnings show which audience definitions are becoming reusable evidence.
- Channel learnings summarize whether the readout is stronger for email, SMS, mixed, or unknown routes.
- Offer/action learnings connect decisions back to the planned CRM action.
- Decision-outcome learnings show how many tests are scaling, retesting, stopping, or awaiting review.
- Confidence learnings help separate higher-certainty evidence from exploratory pilots.

## Why this matters

Commercial analytics teams do not only need one experiment result. They need a memory of what has been tried, which audiences responded, which decisions were made, and which evidence should shape the next plan.

This phase strengthens the project as a job portfolio because it demonstrates a full measurement loop: plan, assign, schedule, read out, decide, and retain reusable learning.

## Production boundary

The current learning library is generated from deterministic demo readouts. A production version would persist experiments in a governed registry, link them to campaign delivery logs, add reviewer identity and approval status, deduplicate repeated tests, and expose searchable evidence by team, market, channel, and customer segment.

## Next step

Phase 39 should add portfolio polish around the CRM workflow, such as a concise case-study section on the GitHub Pages site that explains the end-to-end lifecycle from retention opportunity to reusable learning.
