from __future__ import annotations

from marketing_effectiveness_lab.analytics import prepare_weekly_frame, summarize_kpis
from marketing_effectiveness_lab.budget import (
    allocation_from_shares,
    current_weekly_spend,
    evaluate_budget_scenario,
    roi_weighted_allocation,
)
from marketing_effectiveness_lab.data.generator import generate_weekly_demo_data
from marketing_effectiveness_lab.governance import assess_recommendation_readiness
from marketing_effectiveness_lab.mmm import fit_mmm_foundation_model
from marketing_effectiveness_lab.reporting import (
    build_executive_summary,
    build_model_run_manifest,
    build_model_run_report,
    compare_model_run_manifests,
    model_run_manifest_comparison_csv,
    model_run_manifest_json,
    parse_model_run_manifest_json,
)


def test_executive_summary_contains_business_sections() -> None:
    df, _ = generate_weekly_demo_data(seed=42)
    prepared = prepare_weekly_frame(df)
    kpis = summarize_kpis(prepared)
    mmm_result = fit_mmm_foundation_model(df, holdout_weeks=26)
    current = current_weekly_spend(df, lookback_weeks=13)
    proposed = roi_weighted_allocation(current, mmm_result, sum(current.values()), tilt_strength=0.6)
    scenario = evaluate_budget_scenario(df, mmm_result, proposed, lookback_weeks=13)

    summary = build_executive_summary(kpis, mmm_result, scenario)

    assert summary.headline
    assert len(summary.highlights) == 5
    assert any("contribution profit" in highlight for highlight in summary.highlights)
    assert summary.recommendation
    assert len(summary.caveats) == 3


def test_neutral_scenario_summary_is_not_overstated() -> None:
    df, _ = generate_weekly_demo_data(seed=42)
    prepared = prepare_weekly_frame(df)
    kpis = summarize_kpis(prepared)
    mmm_result = fit_mmm_foundation_model(df, holdout_weeks=26)
    current = current_weekly_spend(df, lookback_weeks=13)
    scenario = evaluate_budget_scenario(df, mmm_result, current, lookback_weeks=13)

    summary = build_executive_summary(kpis, mmm_result, scenario)

    assert "neutral" in summary.headline.lower()
    assert "baseline" in summary.recommendation.lower()


def test_negative_scenario_summary_warns_against_advancing() -> None:
    df, _ = generate_weekly_demo_data(seed=42)
    prepared = prepare_weekly_frame(df)
    kpis = summarize_kpis(prepared)
    mmm_result = fit_mmm_foundation_model(df, holdout_weeks=26)
    current = current_weekly_spend(df, lookback_weeks=13)
    low_response_shares = {column: 1.0 for column in current}
    proposed = allocation_from_shares(current, low_response_shares, 0.0)
    scenario = evaluate_budget_scenario(df, mmm_result, proposed, lookback_weeks=13)

    summary = build_executive_summary(kpis, mmm_result, scenario)

    assert scenario.summary["weekly_contribution_change_gbp"] < 0
    assert "weaker" in summary.headline.lower()
    assert "do not advance" in summary.recommendation.lower()


def test_model_run_report_contains_review_sections() -> None:
    df, _ = generate_weekly_demo_data(seed=42)
    prepared = prepare_weekly_frame(df)
    kpis = summarize_kpis(prepared)
    mmm_result = fit_mmm_foundation_model(df, holdout_weeks=26)
    current = current_weekly_spend(df, lookback_weeks=13)
    scenario = evaluate_budget_scenario(df, mmm_result, current, lookback_weeks=13)
    summary = build_executive_summary(kpis, mmm_result, scenario)
    readiness = assess_recommendation_readiness(
        mmm_result,
        scenario,
        weekly_rows=len(prepared),
        evidence_quality=None,
    )

    report = build_model_run_report(
        kpis,
        mmm_result,
        scenario,
        summary,
        data_source_label="Demo data",
        model_label="MMM foundation",
        row_count=len(prepared),
        first_week=str(prepared["week_start"].min().date()),
        last_week=str(prepared["week_start"].max().date()),
        recommendation_readiness=readiness,
    )

    assert report.startswith("# Marketing Effectiveness Model Run Report")
    assert "## Run Context" in report
    assert "- Data source: Demo data" in report
    assert "## Model Diagnostics" in report
    assert "## Budget Scenario" in report
    assert "## Recommendation Readiness" in report
    assert "## Review Notes" in report
    assert "not a production approval record" in report


def test_model_run_manifest_is_stable_and_machine_readable() -> None:
    df, _ = generate_weekly_demo_data(seed=42)
    prepared = prepare_weekly_frame(df)
    kpis = summarize_kpis(prepared)
    mmm_result = fit_mmm_foundation_model(df, holdout_weeks=26)
    current = current_weekly_spend(df, lookback_weeks=13)
    scenario = evaluate_budget_scenario(df, mmm_result, current, lookback_weeks=13)
    summary = build_executive_summary(kpis, mmm_result, scenario)
    readiness = assess_recommendation_readiness(
        mmm_result,
        scenario,
        weekly_rows=len(prepared),
        evidence_quality=None,
    )

    manifest = build_model_run_manifest(
        kpis,
        mmm_result,
        scenario,
        summary,
        data_source_label="Demo data",
        model_label="MMM foundation",
        row_count=len(prepared),
        first_week=str(prepared["week_start"].min().date()),
        last_week=str(prepared["week_start"].max().date()),
        recommendation_readiness=readiness,
    )
    duplicate_manifest = build_model_run_manifest(
        kpis,
        mmm_result,
        scenario,
        summary,
        data_source_label="Demo data",
        model_label="MMM foundation",
        row_count=len(prepared),
        first_week=str(prepared["week_start"].min().date()),
        last_week=str(prepared["week_start"].max().date()),
        recommendation_readiness=readiness,
    )

    assert manifest["schema_version"] == "1.0"
    assert manifest["run_id"] == duplicate_manifest["run_id"]
    assert manifest["run_context"]["data_source"] == "Demo data"
    assert "recommendation_readiness" in manifest
    assert len(manifest["top_media_contributions"]) > 0

    manifest_json = model_run_manifest_json(manifest)
    assert manifest_json.endswith("\n")
    assert '"run_id"' in manifest_json


def test_model_run_manifest_comparison_ranks_uploaded_artifacts() -> None:
    df, _ = generate_weekly_demo_data(seed=42)
    prepared = prepare_weekly_frame(df)
    kpis = summarize_kpis(prepared)
    mmm_result = fit_mmm_foundation_model(df, holdout_weeks=26)
    current = current_weekly_spend(df, lookback_weeks=13)
    baseline_scenario = evaluate_budget_scenario(df, mmm_result, current, lookback_weeks=13)
    proposed = roi_weighted_allocation(current, mmm_result, sum(current.values()), tilt_strength=0.6)
    roi_scenario = evaluate_budget_scenario(df, mmm_result, proposed, lookback_weeks=13)

    manifests = []
    for label, scenario in [
        ("Current mix", baseline_scenario),
        ("ROI-weighted tilt", roi_scenario),
    ]:
        summary = build_executive_summary(kpis, mmm_result, scenario)
        readiness = assess_recommendation_readiness(
            mmm_result,
            scenario,
            weekly_rows=len(prepared),
            evidence_quality=None,
        )
        manifest = build_model_run_manifest(
            kpis,
            mmm_result,
            scenario,
            summary,
            data_source_label="Demo data",
            model_label=label,
            row_count=len(prepared),
            first_week=str(prepared["week_start"].min().date()),
            last_week=str(prepared["week_start"].max().date()),
            recommendation_readiness=readiness,
        )
        manifests.append(parse_model_run_manifest_json(model_run_manifest_json(manifest)))

    comparison = compare_model_run_manifests(manifests)

    assert len(comparison) == 2
    assert comparison["comparison_rank"].tolist() == [1, 2]
    assert set(comparison["active_model"]) == {"Current mix", "ROI-weighted tilt"}
    assert comparison["readiness_score"].iloc[0] >= comparison["readiness_score"].iloc[1]
    assert "weekly_profit_change_gbp" in comparison.columns
    assert comparison["top_contribution_channel"].str.len().min() > 0

    comparison_csv = model_run_manifest_comparison_csv(comparison)
    assert comparison_csv.startswith("comparison_rank,run_id")
    assert "weekly_profit_change_gbp" in comparison_csv
