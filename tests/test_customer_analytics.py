from __future__ import annotations

from marketing_effectiveness_lab.customer import (
    acquisition_channel_quality,
    build_crm_experiment_artifact,
    cohort_retention,
    compare_crm_experiment_artifacts,
    crm_experiment_artifact_comparison_csv,
    crm_experiment_artifact_json,
    crm_experiment_brief_markdown,
    crm_experiment_checklist,
    crm_experiment_design,
    crm_experiment_portfolio_csv,
    crm_incrementality_portfolio,
    crm_incrementality_summary,
    customer_future_value_backtest,
    customer_value_windows,
    lapse_value_segment_summary,
    new_vs_returning_summary,
    parse_crm_experiment_artifact_json,
    prepare_customer_tables,
    retention_segment_action_plan,
    score_customer_lapse_value,
    segment_summary,
    summarize_crm_experiment_portfolio,
    summarize_customer_kpis,
)
from marketing_effectiveness_lab.data.customer_generator import generate_customer_demo_data


def test_customer_kpis_summarize_ecommerce_economics() -> None:
    dataset = generate_customer_demo_data(seed=42, customer_count=800)
    tables = prepare_customer_tables(dataset.as_tables())

    summary = summarize_customer_kpis(
        tables["customers"],
        tables["orders"],
        tables["customer_segments"],
    )

    assert summary.total_customers == 800
    assert summary.ordering_customers == 800
    assert summary.repeat_customers > 0
    assert 0 < summary.repeat_purchase_rate < 1
    assert summary.revenue_gbp > summary.gross_margin_gbp > 0
    assert 0 < summary.gross_margin_rate < 1
    assert 0 < summary.contactable_rate <= 1


def test_segment_summary_preserves_customer_counts() -> None:
    dataset = generate_customer_demo_data(seed=42, customer_count=800)
    tables = prepare_customer_tables(dataset.as_tables())

    summary = segment_summary(tables["customer_segments"])

    assert summary["customers"].sum() == 800
    assert summary["gross_margin_gbp"].sum() > 0
    assert summary["gross_margin_per_customer_gbp"].min() >= 0
    assert set(summary["value_segment"]) == {"Low value", "Mid value", "High value", "VIP"}


def test_acquisition_channel_quality_has_repeat_and_margin_fields() -> None:
    dataset = generate_customer_demo_data(seed=42, customer_count=800)
    tables = prepare_customer_tables(dataset.as_tables())

    quality = acquisition_channel_quality(tables["customers"], tables["customer_segments"])

    assert quality["customers"].sum() == 800
    assert quality["gross_margin_per_customer_gbp"].max() > 0
    assert quality["repeat_purchase_rate"].between(0, 1).all()
    assert quality["contactable_rate"].between(0, 1).all()


def test_cohort_retention_returns_monthly_curve() -> None:
    dataset = generate_customer_demo_data(seed=42, customer_count=800)
    tables = prepare_customer_tables(dataset.as_tables())

    retention = cohort_retention(tables["customers"], tables["orders"], max_month_number=6)

    assert retention["month_number"].min() == 0
    assert retention["month_number"].max() <= 6
    assert retention["retention_rate"].between(0, 1).all()
    assert retention["cumulative_gross_margin_gbp"].min() > 0
    assert retention["cohort_label"].str.len().eq(7).all()


def test_new_vs_returning_summary_splits_first_and_repeat_orders() -> None:
    dataset = generate_customer_demo_data(seed=42, customer_count=800)
    tables = prepare_customer_tables(dataset.as_tables())

    summary = new_vs_returning_summary(tables["customers"], tables["orders"])

    assert set(summary["customer_order_type"]) == {
        "New customer orders",
        "Returning customer orders",
    }
    assert summary["orders"].sum() == len(tables["orders"])
    assert summary["gross_margin_gbp"].sum() == tables["orders"]["gross_margin_gbp"].sum()


def test_customer_value_windows_are_cumulative() -> None:
    dataset = generate_customer_demo_data(seed=42, customer_count=800)
    tables = prepare_customer_tables(dataset.as_tables())

    values = customer_value_windows(tables["customers"], tables["orders"])

    assert len(values) == 800
    assert values["gross_margin_30d_gbp"].le(values["gross_margin_180d_gbp"]).all()
    assert values["revenue_90d_gbp"].le(values["revenue_180d_gbp"]).all()
    assert values["orders_180d"].ge(1).all()


def test_customer_future_value_backtest_returns_segment_baseline() -> None:
    dataset = generate_customer_demo_data(seed=42, customer_count=800)
    tables = prepare_customer_tables(dataset.as_tables())

    backtest = customer_future_value_backtest(
        tables["customers"],
        tables["orders"],
        cutoff_date="2025-01-01",
        horizon_days=180,
    )

    assert {"lifecycle_segment", "value_segment", "expected_future_margin_gbp"}.issubset(backtest.columns)
    assert backtest["customers"].sum() > 0
    assert backtest["expected_future_margin_gbp"].ge(0).all()
    assert backtest["mean_absolute_error_gbp"].ge(0).all()
    assert backtest["repeat_rate_in_horizon"].between(0, 1).all()


def test_score_customer_lapse_value_produces_risk_bands_and_expected_margin() -> None:
    dataset = generate_customer_demo_data(seed=42, customer_count=800)
    tables = prepare_customer_tables(dataset.as_tables())

    scored = score_customer_lapse_value(
        tables["customers"],
        tables["orders"],
        as_of_date="2025-12-31",
        calibration_cutoff_date="2025-01-01",
        horizon_days=180,
    )

    assert len(scored) == 800
    assert scored["expected_future_margin_gbp"].ge(0).all()
    assert scored["lapse_risk_score"].between(0, 100).all()
    assert set(scored["lapse_risk_band"]).issubset({"Low", "Medium", "High"})
    assert scored["lapse_risk_score"].is_monotonic_decreasing


def test_lapse_value_segment_summary_preserves_customer_count() -> None:
    dataset = generate_customer_demo_data(seed=42, customer_count=800)
    tables = prepare_customer_tables(dataset.as_tables())
    scored = score_customer_lapse_value(
        tables["customers"],
        tables["orders"],
        as_of_date="2025-12-31",
        calibration_cutoff_date="2025-01-01",
        horizon_days=180,
    )

    summary = lapse_value_segment_summary(scored)

    assert summary["customers"].sum() == 800
    assert summary["expected_future_margin_gbp"].sum() >= 0
    assert summary["avg_lapse_risk_score"].between(0, 100).all()
    assert summary["contactable_rate"].between(0, 1).all()


def test_crm_incrementality_summary_estimates_holdout_lift_and_profit() -> None:
    dataset = generate_customer_demo_data(seed=42, customer_count=800)
    tables = prepare_customer_tables(dataset.as_tables())

    summary = crm_incrementality_summary(tables["crm_campaigns"], tables["crm_events"])

    assert len(summary) == len(tables["crm_campaigns"])
    assert summary["target_customers"].gt(0).all()
    assert summary["holdout_customers"].ge(0).all()
    assert summary["holdout_customers"].gt(0).any()
    assert summary["target_conversion_rate"].between(0, 1).all()
    assert summary["holdout_conversion_rate"].between(0, 1).all()
    assert summary["conversion_lift_lower"].le(summary["conversion_lift"]).all()
    assert summary["conversion_lift_upper"].ge(summary["conversion_lift"]).all()
    assert summary["unsubscribe_rate"].between(0, 1).all()
    assert set(summary["evidence_status"]).issubset(
        {"Positive", "Review", "Negative", "Needs more data"}
    )


def test_crm_incrementality_portfolio_rolls_up_campaign_diagnostics() -> None:
    dataset = generate_customer_demo_data(seed=42, customer_count=800)
    tables = prepare_customer_tables(dataset.as_tables())
    summary = crm_incrementality_summary(tables["crm_campaigns"], tables["crm_events"])

    portfolio = crm_incrementality_portfolio(summary)

    assert portfolio["campaigns"] == len(summary)
    assert portfolio["positive_campaigns"] >= 0
    assert portfolio["review_campaigns"] >= 0
    assert isinstance(portfolio["total_incremental_profit_gbp"], float)
    assert isinstance(portfolio["total_incremental_margin_gbp"], float)


def test_retention_segment_action_plan_combines_value_risk_and_crm_evidence() -> None:
    dataset = generate_customer_demo_data(seed=42, customer_count=800)
    tables = prepare_customer_tables(dataset.as_tables())
    scored = score_customer_lapse_value(
        tables["customers"],
        tables["orders"],
        as_of_date="2025-12-31",
        calibration_cutoff_date="2025-01-01",
        horizon_days=180,
    )
    crm_summary = crm_incrementality_summary(tables["crm_campaigns"], tables["crm_events"])

    plan = retention_segment_action_plan(scored, crm_summary)

    assert plan["customers"].sum() == 800
    assert plan["contactable_customers"].le(plan["customers"]).all()
    assert plan["contactable_rate"].between(0, 1).all()
    assert plan["risk_weighted_margin_gbp"].ge(0).all()
    assert plan["recommended_holdout_rate"].between(0, 0.25).all()
    assert plan["max_incentive_cost_per_customer_gbp"].ge(0).all()
    assert plan["testable_customers"].ge(0).all()
    assert set(plan["recommended_action"]).issubset(
        {
            "Scale tested CRM",
            "Run holdout test",
            "Retest offer before scaling",
            "Suppress incentive",
            "Monitor",
            "No contactable audience",
        }
    )
    assert plan["recommended_action"].isin({"Run holdout test", "Retest offer before scaling"}).any()


def test_crm_experiment_design_returns_launch_plan_and_checklist() -> None:
    dataset = generate_customer_demo_data(seed=42, customer_count=800)
    tables = prepare_customer_tables(dataset.as_tables())
    scored = score_customer_lapse_value(
        tables["customers"],
        tables["orders"],
        as_of_date="2025-12-31",
        calibration_cutoff_date="2025-01-01",
        horizon_days=180,
    )
    crm_summary = crm_incrementality_summary(tables["crm_campaigns"], tables["crm_events"])
    plan = retention_segment_action_plan(scored, crm_summary)
    testable_segment = plan[
        plan["recommended_action"].isin({"Run holdout test", "Retest offer before scaling"})
    ].iloc[0]

    design = crm_experiment_design(
        testable_segment,
        baseline_conversion_rate=0.05,
        minimum_detectable_lift=0.025,
        test_duration_days=21,
    )
    checklist = crm_experiment_checklist(design)

    assert design["contactable_customers"] == int(testable_segment["contactable_customers"])
    assert design["treatment_customers"] + design["holdout_customers"] == design["contactable_customers"]
    assert design["required_sample_per_group"] > 0
    assert design["effective_sample_per_group"] <= design["holdout_customers"]
    assert design["launch_readiness"] in {
        "Ready to test",
        "Directional pilot",
        "Underpowered",
        "Do not launch",
    }
    assert design["expected_incremental_margin_at_mde_gbp"] >= 0
    assert set(checklist.columns) == {"check_area", "requirement", "status"}
    assert len(checklist) == 5
    assert checklist["status"].isin({"Ready", "Review", "Blocked"}).all()


def test_crm_experiment_artifact_exports_json_and_markdown_brief() -> None:
    dataset = generate_customer_demo_data(seed=42, customer_count=800)
    tables = prepare_customer_tables(dataset.as_tables())
    scored = score_customer_lapse_value(
        tables["customers"],
        tables["orders"],
        as_of_date="2025-12-31",
        calibration_cutoff_date="2025-01-01",
        horizon_days=180,
    )
    crm_summary = crm_incrementality_summary(tables["crm_campaigns"], tables["crm_events"])
    plan = retention_segment_action_plan(scored, crm_summary)
    testable_segment = plan[
        plan["recommended_action"].isin({"Run holdout test", "Retest offer before scaling"})
    ].iloc[0]
    design = crm_experiment_design(testable_segment)
    checklist = crm_experiment_checklist(design)

    artifact = build_crm_experiment_artifact(testable_segment, design, checklist)
    duplicate_artifact = build_crm_experiment_artifact(testable_segment, design, checklist)
    artifact_json = crm_experiment_artifact_json(artifact)
    brief = crm_experiment_brief_markdown(artifact)

    assert artifact["schema_version"] == "1.0"
    assert artifact["artifact_type"] == "crm_experiment_brief"
    assert artifact["artifact_id"] == duplicate_artifact["artifact_id"]
    assert '"artifact_id"' in artifact_json
    assert artifact_json.endswith("\n")
    assert brief.startswith("# CRM Experiment Brief")
    assert "## Launch Checklist" in brief
    assert "not production approval" in brief


def test_crm_experiment_artifact_comparison_ranks_saved_artifacts() -> None:
    dataset = generate_customer_demo_data(seed=42, customer_count=800)
    tables = prepare_customer_tables(dataset.as_tables())
    scored = score_customer_lapse_value(
        tables["customers"],
        tables["orders"],
        as_of_date="2025-12-31",
        calibration_cutoff_date="2025-01-01",
        horizon_days=180,
    )
    crm_summary = crm_incrementality_summary(tables["crm_campaigns"], tables["crm_events"])
    plan = retention_segment_action_plan(scored, crm_summary)
    candidates = plan[
        plan["recommended_action"].isin(
            {"Scale tested CRM", "Run holdout test", "Retest offer before scaling"}
        )
    ].head(4)

    artifacts = []
    for _, candidate in candidates.iterrows():
        design = crm_experiment_design(candidate)
        checklist = crm_experiment_checklist(design)
        artifact = build_crm_experiment_artifact(candidate, design, checklist)
        artifacts.append(parse_crm_experiment_artifact_json(crm_experiment_artifact_json(artifact)))

    comparison = compare_crm_experiment_artifacts(artifacts)
    comparison_csv = crm_experiment_artifact_comparison_csv(comparison)

    assert len(comparison) == len(artifacts)
    assert comparison["comparison_rank"].tolist() == list(range(1, len(artifacts) + 1))
    assert comparison["priority_score"].is_monotonic_decreasing
    assert comparison["artifact_id"].notna().all()
    assert comparison["expected_incremental_margin_at_mde_gbp"].ge(0).all()
    assert comparison_csv.startswith("comparison_rank,artifact_id")
    assert "launch_readiness" in comparison_csv


def test_crm_experiment_portfolio_summarizes_selected_ranked_artifacts() -> None:
    dataset = generate_customer_demo_data(seed=42, customer_count=800)
    tables = prepare_customer_tables(dataset.as_tables())
    scored = score_customer_lapse_value(
        tables["customers"],
        tables["orders"],
        as_of_date="2025-12-31",
        calibration_cutoff_date="2025-01-01",
        horizon_days=180,
    )
    crm_summary = crm_incrementality_summary(tables["crm_campaigns"], tables["crm_events"])
    plan = retention_segment_action_plan(scored, crm_summary)
    candidates = plan[
        plan["recommended_action"].isin(
            {"Scale tested CRM", "Run holdout test", "Retest offer before scaling"}
        )
    ].head(5)
    artifacts = []
    for _, candidate in candidates.iterrows():
        design = crm_experiment_design(candidate)
        checklist = crm_experiment_checklist(design)
        artifacts.append(build_crm_experiment_artifact(candidate, design, checklist))

    comparison = compare_crm_experiment_artifacts(artifacts)
    portfolio = summarize_crm_experiment_portfolio(comparison, top_n=3)
    selected = comparison.sort_values("comparison_rank").head(3)
    portfolio_csv = crm_experiment_portfolio_csv(comparison, top_n=3)

    assert portfolio["experiments"] == 3
    assert portfolio["contactable_customers"] == selected["contactable_customers"].sum()
    assert portfolio["holdout_customers"] == selected["holdout_customers"].sum()
    assert 0 <= portfolio["portfolio_holdout_rate"] <= 1
    assert portfolio["expected_incremental_margin_at_mde_gbp"] == selected[
        "expected_incremental_margin_at_mde_gbp"
    ].sum()
    assert portfolio["portfolio_status"] in {
        "Launch-ready portfolio",
        "Mixed readiness",
        "Pilot queue",
        "Holdout burden review",
        "Review before launch",
    }
    assert portfolio_csv.startswith("comparison_rank,artifact_id")
