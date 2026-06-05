from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from marketing_effectiveness_lab import budget as budget_tools
from marketing_effectiveness_lab.analytics import (
    CHANNEL_LABELS,
    channel_summary,
    mmm_readiness_checks,
    prepare_weekly_frame,
    promotion_summary,
    spend_columns,
    summarize_kpis,
    weekly_spend_long,
)
from marketing_effectiveness_lab.bayesian import fit_bayesian_mmm
from marketing_effectiveness_lab.budget import (
    allocation_from_shares,
    current_weekly_spend,
    evaluate_budget_scenario,
    roi_weighted_allocation,
)
from marketing_effectiveness_lab.calibration import (
    apply_lift_calibration,
    apply_lift_calibration_to_intervals,
    approved_lift_tests,
    assess_lift_test_evidence,
    calibration_factors,
    demo_lift_test_calibrations,
    lift_test_template_csv,
    validate_lift_test_csv_text,
)
from marketing_effectiveness_lab.data.assembly import (
    WeeklyAssemblyResult,
    assemble_connector_csv_texts,
)
from marketing_effectiveness_lab.data.connectors import (
    CONNECTOR_SPECS,
    connector_schema_dataframe,
    connector_template_csv,
    validate_connector_csv_text,
)
from marketing_effectiveness_lab.data.diagnostics import assembled_weekly_diagnostics
from marketing_effectiveness_lab.data.generator import generate_and_validate
from marketing_effectiveness_lab.data.importer import template_csv, validate_csv_text
from marketing_effectiveness_lab.data.schema import validate_weekly_dataset
from marketing_effectiveness_lab.mmm import calibrate_mmm_parameters, fit_mmm_foundation_model
from marketing_effectiveness_lab.modeling import fit_baseline_model
from marketing_effectiveness_lab.reporting import build_executive_summary
from marketing_effectiveness_lab.uncertainty import simulate_mmm_uncertainty

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "demo" / "fashion_retail_weekly.csv"
DEMO_OUTPUT_DIR = PROJECT_ROOT / "data" / "demo"

PAGE_TITLE = "Marketing Effectiveness Lab"
optimize_budget_allocation = getattr(budget_tools, "optimize_budget_allocation", None)


st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon="M",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown(
    """
    <style>
    :root {
        --mel-ink: #1f2933;
        --mel-muted: #65717f;
        --mel-line: #d9e2ec;
        --mel-bg: #f6f8fa;
        --mel-green: #2f7d64;
        --mel-coral: #c65f4b;
    }
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1420px;
    }
    h1, h2, h3 {
        color: var(--mel-ink);
        letter-spacing: 0;
    }
    [data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid var(--mel-line);
        border-radius: 8px;
        padding: 14px 16px;
    }
    [data-testid="stMetricLabel"] {
        color: var(--mel-muted);
    }
    [data-testid="stMetricValue"] {
        color: var(--mel-ink);
    }
    section[data-testid="stSidebar"] {
        background: #f8fafc;
        border-right: 1px solid var(--mel-line);
    }
    .mel-caption {
        color: var(--mel-muted);
        font-size: 0.94rem;
        margin-top: -0.45rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def gbp(value: float) -> str:
    if abs(value) >= 1_000_000:
        return f"GBP {value / 1_000_000:,.1f}M"
    if abs(value) >= 1_000:
        return f"GBP {value / 1_000:,.0f}K"
    return f"GBP {value:,.0f}"


def integer(value: float) -> str:
    return f"{value:,.0f}"


def percent(value: float) -> str:
    return f"{value * 100:,.1f}%"


def x_value(value: float) -> str:
    return f"{value:,.1f}x"


@st.cache_data(show_spinner=False)
def load_demo_data() -> pd.DataFrame:
    if not DATA_PATH.exists():
        generate_and_validate(DEMO_OUTPUT_DIR)
    raw = pd.read_csv(DATA_PATH)
    errors = validate_weekly_dataset(raw)
    if errors:
        st.error("Dataset validation failed.")
        for error in errors:
            st.write(f"- {error}")
        st.stop()
    return prepare_weekly_frame(raw)


@st.cache_data(show_spinner=False)
def parse_uploaded_csv(csv_text: str) -> tuple[pd.DataFrame | None, list[str]]:
    parsed, errors = validate_csv_text(csv_text)
    if errors or parsed is None:
        return None, errors
    return prepare_weekly_frame(parsed), []


@st.cache_data(show_spinner=False)
def parse_connector_csv(
    connector_key: str,
    csv_text: str,
) -> tuple[pd.DataFrame | None, list[str]]:
    return validate_connector_csv_text(connector_key, csv_text)


@st.cache_data(show_spinner=False)
def assemble_connector_uploads(csv_text_by_connector: dict[str, str]) -> WeeklyAssemblyResult:
    return assemble_connector_csv_texts(csv_text_by_connector)


@st.cache_data(show_spinner=False)
def diagnose_assembled_weekly_data(
    weekly_dataset: pd.DataFrame,
    source_summary: pd.DataFrame,
    validation_errors: list[str],
) -> pd.DataFrame:
    return assembled_weekly_diagnostics(
        weekly_dataset,
        source_summary,
        validation_errors,
    )


def select_dataset() -> tuple[pd.DataFrame, str]:
    with st.sidebar:
        st.header("Data source")
        source = st.radio(
            "Dataset",
            ["Demo data", "Upload CSV", "Connector assembly"],
            horizontal=False,
        )
        st.download_button(
            "Download CSV template",
            data=template_csv(rows=12),
            file_name="marketing_effectiveness_template.csv",
            mime="text/csv",
            use_container_width=True,
        )
        with st.expander("Connector templates"):
            connector_labels = {spec.label: spec.key for spec in CONNECTOR_SPECS}
            selected_connector_label = st.selectbox(
                "Export type",
                options=list(connector_labels),
            )
            selected_connector_key = connector_labels[selected_connector_label]
            st.download_button(
                "Download connector template",
                data=connector_template_csv(selected_connector_key),
                file_name=f"{selected_connector_key}_weekly_template.csv",
                mime="text/csv",
                use_container_width=True,
            )
            st.dataframe(
                connector_schema_dataframe(selected_connector_key),
                use_container_width=True,
                hide_index=True,
            )
            connector_upload = st.file_uploader(
                "Validate connector CSV",
                type=["csv"],
                key=f"{selected_connector_key}_connector_upload",
            )
            if connector_upload is not None:
                connector_csv_text = connector_upload.getvalue().decode("utf-8-sig")
                connector_df, connector_errors = parse_connector_csv(
                    selected_connector_key,
                    connector_csv_text,
                )
                if connector_errors or connector_df is None:
                    st.error("Connector CSV failed validation.")
                    for error in connector_errors:
                        st.write(f"- {error}")
                else:
                    st.success(
                        f"Validated {len(connector_df):,} rows for {selected_connector_label}."
                    )

        if source == "Connector assembly":
            st.markdown("**Assemble MMM dataset**")
            st.caption("Upload Shopify/ecommerce plus optional platform exports.")
            connector_csv_texts = {}
            for spec in CONNECTOR_SPECS:
                assembly_upload = st.file_uploader(
                    spec.label,
                    type=["csv"],
                    key=f"assembly_upload_{spec.key}",
                )
                if assembly_upload is not None:
                    connector_csv_texts[spec.key] = assembly_upload.getvalue().decode(
                        "utf-8-sig"
                    )

            if not connector_csv_texts:
                st.info("Upload connector CSVs to assemble the weekly MMM dataset.")
                st.stop()

            assembly_result = assemble_connector_uploads(connector_csv_texts)
            if not assembly_result.source_summary.empty:
                st.dataframe(
                    assembly_result.source_summary,
                    use_container_width=True,
                    hide_index=True,
                )

            assembly_diagnostics = diagnose_assembled_weekly_data(
                assembly_result.weekly_dataset,
                assembly_result.source_summary,
                assembly_result.validation_errors,
            )
            st.markdown("**Assembly diagnostics**")
            st.dataframe(
                assembly_diagnostics,
                use_container_width=True,
                hide_index=True,
            )

            if assembly_result.validation_errors:
                st.error("Connector assembly failed validation.")
                for error in assembly_result.validation_errors:
                    st.write(f"- {error}")
                if not assembly_result.weekly_dataset.empty:
                    st.download_button(
                        "Download assembled CSV for review",
                        data=assembly_result.weekly_dataset.to_csv(index=False),
                        file_name="assembled_marketing_effectiveness_weekly.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )
                st.stop()

            st.success(f"Assembled {len(assembly_result.weekly_dataset):,} weekly rows.")
            st.download_button(
                "Download assembled weekly CSV",
                data=assembly_result.weekly_dataset.to_csv(index=False),
                file_name="assembled_marketing_effectiveness_weekly.csv",
                mime="text/csv",
                use_container_width=True,
            )
            if len(assembly_result.weekly_dataset) <= 56:
                st.warning("MMM views need at least 57 weekly rows after assembly.")
                st.stop()
            return (
                prepare_weekly_frame(assembly_result.weekly_dataset),
                "Connector assembly",
            )

        if source == "Upload CSV":
            uploaded_file = st.file_uploader("Upload weekly marketing CSV", type=["csv"])
            if uploaded_file is None:
                st.info("Upload a CSV that follows the documented weekly schema.")
                st.stop()
            csv_text = uploaded_file.getvalue().decode("utf-8-sig")
            uploaded_df, errors = parse_uploaded_csv(csv_text)
            if errors or uploaded_df is None:
                st.error("Uploaded CSV failed validation.")
                for error in errors:
                    st.write(f"- {error}")
                st.stop()
            if len(uploaded_df) <= 56:
                st.error("Uploaded data needs at least 57 weekly rows for the current holdout models.")
                st.stop()
            st.success(f"Loaded {len(uploaded_df):,} weekly rows from uploaded CSV.")
            return uploaded_df, uploaded_file.name

        demo_df = load_demo_data()
        st.caption("Using generated demo data. No private data is stored.")
        return demo_df, "Demo data"


def line_with_average(
    df: pd.DataFrame,
    y: str,
    y_avg: str,
    title: str,
    y_title: str,
    primary_color: str,
) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["week_start"],
            y=df[y],
            mode="lines",
            name=title,
            line={"color": primary_color, "width": 1.4},
            opacity=0.45,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["week_start"],
            y=df[y_avg],
            mode="lines",
            name="4-week average",
            line={"color": "#1f2933", "width": 2.6},
        )
    )
    fig.update_layout(
        title=title,
        height=360,
        margin={"l": 12, "r": 12, "t": 48, "b": 24},
        yaxis_title=y_title,
        xaxis_title=None,
        legend_orientation="h",
        legend_y=1.08,
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
    )
    return fig


def filtered_frame(df: pd.DataFrame) -> pd.DataFrame:
    min_date = df["week_start"].min().date()
    max_date = df["week_start"].max().date()

    with st.sidebar:
        st.header("Controls")
        date_range = st.date_input(
            "Date range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )
        channels = st.multiselect(
            "Spend channels",
            options=list(CHANNEL_LABELS.values()),
            default=list(CHANNEL_LABELS.values()),
        )
        st.divider()
        show_promotions = st.checkbox("Highlight promo weeks", value=True)
        st.caption("Demo data follows a real-data-ready schema for weekly marketing measurement.")

    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
    else:
        start_date, end_date = pd.to_datetime(min_date), pd.to_datetime(max_date)

    selected = df[(df["week_start"] >= start_date) & (df["week_start"] <= end_date)].copy()
    selected.attrs["channels"] = channels
    selected.attrs["show_promotions"] = show_promotions
    return selected


df, data_source_label = select_dataset()
selected_df = filtered_frame(df)
selected_channels = selected_df.attrs["channels"]
show_promotions = selected_df.attrs["show_promotions"]

st.title(PAGE_TITLE)
st.markdown(
    '<p class="mel-caption">Analyst dashboard for UK fashion ecommerce marketing performance, '
    "MMM readiness, and commercial diagnostics.</p>",
    unsafe_allow_html=True,
)
st.caption(f"Data source: {data_source_label}")

if selected_df.empty:
    st.warning("No rows available for the selected date range.")
    st.stop()

kpis = summarize_kpis(selected_df)

metric_cols = st.columns(5)
metric_cols[0].metric("Revenue", gbp(kpis.revenue_gbp))
metric_cols[1].metric("Media spend", gbp(kpis.media_spend_gbp))
metric_cols[2].metric("Blended ROAS", f"{kpis.blended_roas:,.1f}x")
metric_cols[3].metric("Orders", integer(kpis.orders))
metric_cols[4].metric("New customers", integer(kpis.new_customers))

st.divider()

trend_left, trend_right = st.columns((1.35, 1))
with trend_left:
    revenue_fig = line_with_average(
        selected_df,
        y="revenue_gbp",
        y_avg="revenue_4w_avg",
        title="Weekly revenue",
        y_title="Revenue GBP",
        primary_color="#2f7d64",
    )
    if show_promotions:
        promo_weeks = selected_df[selected_df["promotion_flag"] == 1]
        revenue_fig.add_trace(
            go.Scatter(
                x=promo_weeks["week_start"],
                y=promo_weeks["revenue_gbp"],
                mode="markers",
                name="Promo week",
                marker={"color": "#c65f4b", "size": 7},
            )
        )
    st.plotly_chart(revenue_fig, use_container_width=True)

with trend_right:
    spend_fig = line_with_average(
        selected_df,
        y="total_media_spend_gbp",
        y_avg="media_spend_4w_avg",
        title="Weekly media spend",
        y_title="Spend GBP",
        primary_color="#4b6f9c",
    )
    st.plotly_chart(spend_fig, use_container_width=True)

mix_left, mix_right = st.columns((1.05, 1))
with mix_left:
    long_spend = weekly_spend_long(selected_df)
    if selected_channels:
        long_spend = long_spend[long_spend["channel"].isin(selected_channels)]
    spend_mix_fig = px.area(
        long_spend,
        x="week_start",
        y="spend_gbp",
        color="channel",
        title="Channel spend mix",
        labels={"week_start": "", "spend_gbp": "Spend GBP", "channel": "Channel"},
        color_discrete_sequence=["#2f7d64", "#4b6f9c", "#c65f4b", "#9a7b3f", "#6b7280", "#7c6aa6"],
    )
    spend_mix_fig.update_layout(
        height=390,
        margin={"l": 12, "r": 12, "t": 48, "b": 24},
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        legend_orientation="h",
        legend_y=1.08,
    )
    st.plotly_chart(spend_mix_fig, use_container_width=True)

with mix_right:
    channel_df = channel_summary(selected_df)
    if selected_channels:
        channel_df = channel_df[channel_df["channel"].isin(selected_channels)]
    bar_fig = px.bar(
        channel_df,
        x="spend_gbp",
        y="channel",
        orientation="h",
        title="Total spend by channel",
        labels={"spend_gbp": "Spend GBP", "channel": ""},
        color="spend_share",
        color_continuous_scale=["#dfe7e2", "#2f7d64"],
    )
    bar_fig.update_layout(
        height=390,
        margin={"l": 12, "r": 12, "t": 48, "b": 24},
        yaxis={"categoryorder": "total ascending"},
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        coloraxis_showscale=False,
    )
    st.plotly_chart(bar_fig, use_container_width=True)

st.subheader("Analyst Diagnostics")
diag_left, diag_mid, diag_right = st.columns((1.1, 1, 1))

with diag_left:
    st.markdown("**Channel summary**")
    display_channel = channel_df.copy()
    display_channel["spend_gbp"] = display_channel["spend_gbp"].map(gbp)
    display_channel["avg_weekly_spend_gbp"] = display_channel["avg_weekly_spend_gbp"].map(gbp)
    display_channel["spend_share"] = (display_channel["spend_share"] * 100).map(lambda x: f"{x:,.1f}%")
    display_channel["corr_with_revenue"] = display_channel["corr_with_revenue"].map(lambda x: f"{x:,.2f}")
    st.dataframe(display_channel, use_container_width=True, hide_index=True)

with diag_mid:
    st.markdown("**Promotion comparison**")
    promo_df = promotion_summary(selected_df)
    promo_display = promo_df.copy()
    promo_display["avg_revenue_gbp"] = promo_display["avg_revenue_gbp"].map(gbp)
    promo_display["avg_media_spend_gbp"] = promo_display["avg_media_spend_gbp"].map(gbp)
    promo_display["avg_promotion_depth_pct"] = promo_display["avg_promotion_depth_pct"].map(
        lambda x: f"{x:,.1f}%"
    )
    promo_display["avg_orders"] = promo_display["avg_orders"].map(integer)
    st.dataframe(promo_display, use_container_width=True, hide_index=True)

with diag_right:
    st.markdown("**MMM readiness**")
    readiness = pd.DataFrame(mmm_readiness_checks(selected_df))
    st.dataframe(readiness, use_container_width=True, hide_index=True)

st.subheader("Correlation Scan")
numeric_cols = [
    "revenue_gbp",
    "orders",
    "new_customers",
    "total_media_spend_gbp",
    *spend_columns(selected_df),
    "promotion_depth_pct",
    "organic_search_sessions",
    "consumer_confidence_index",
    "inflation_rate_pct",
]
corr_df = selected_df[numeric_cols].corr()
label_lookup = {
    "revenue_gbp": "Revenue",
    "orders": "Orders",
    "new_customers": "New customers",
    "total_media_spend_gbp": "Total spend",
    "promotion_depth_pct": "Promo depth",
    "organic_search_sessions": "Organic search",
    "consumer_confidence_index": "Consumer confidence",
    "inflation_rate_pct": "Inflation",
    **CHANNEL_LABELS,
}
corr_df = corr_df.rename(index=label_lookup, columns=label_lookup)
corr_fig = px.imshow(
    corr_df,
    title="Correlation matrix for early modeling review",
    color_continuous_scale=["#c65f4b", "#f7f7f7", "#2f7d64"],
    zmin=-1,
    zmax=1,
    aspect="auto",
)
corr_fig.update_layout(
    height=560,
    margin={"l": 12, "r": 12, "t": 48, "b": 24},
    plot_bgcolor="#ffffff",
    paper_bgcolor="#ffffff",
)
st.plotly_chart(corr_fig, use_container_width=True)

with st.expander("Dataset contract"):
    st.write(
        "This dashboard is running on demo data generated from a real-data-ready weekly schema. "
        "A real company dataset can replace the demo file if it follows the documented fields."
    )
    st.dataframe(selected_df.head(20), use_container_width=True, hide_index=True)

st.divider()
st.subheader("Baseline Econometrics")
st.markdown(
    '<p class="mel-caption">Transparent OLS benchmark using log revenue, log media spend, '
    "promotions, seasonality, trend, organic demand, and macro controls.</p>",
    unsafe_allow_html=True,
)

baseline = fit_baseline_model(df, holdout_weeks=26)
model_metric_cols = st.columns(5)
model_metric_cols[0].metric("Train R-squared", f"{baseline.metrics['train_r_squared']:,.2f}")
model_metric_cols[1].metric(
    "Adj. R-squared", f"{baseline.metrics['train_adjusted_r_squared']:,.2f}"
)
model_metric_cols[2].metric("Train MAPE", percent(baseline.metrics["train_mape"]))
model_metric_cols[3].metric("Holdout MAPE", percent(baseline.metrics["test_mape"]))
model_metric_cols[4].metric("Holdout RMSE", gbp(baseline.metrics["test_rmse_gbp"]))

model_frame = pd.concat(
    [
        baseline.train_frame.assign(sample="Training"),
        baseline.test_frame.assign(sample="Holdout"),
    ],
    ignore_index=True,
)

fit_fig = go.Figure()
fit_fig.add_trace(
    go.Scatter(
        x=model_frame["week_start"],
        y=model_frame["revenue_gbp"],
        mode="lines",
        name="Actual revenue",
        line={"color": "#1f2933", "width": 2.4},
    )
)
fit_fig.add_trace(
    go.Scatter(
        x=model_frame["week_start"],
        y=model_frame["predicted_revenue_gbp"],
        mode="lines",
        name="Baseline prediction",
        line={"color": "#2f7d64", "width": 2.0},
    )
)
holdout_start = baseline.test_frame["week_start"].min()
fit_fig.add_vline(
    x=holdout_start,
    line_dash="dash",
    line_color="#c65f4b",
    annotation_text="Holdout",
    annotation_position="top left",
)
fit_fig.update_layout(
    title="Actual vs baseline predicted revenue",
    height=430,
    margin={"l": 12, "r": 12, "t": 48, "b": 24},
    yaxis_title="Revenue GBP",
    xaxis_title=None,
    legend_orientation="h",
    legend_y=1.08,
    plot_bgcolor="#ffffff",
    paper_bgcolor="#ffffff",
)
st.plotly_chart(fit_fig, use_container_width=True)

coef_left, coef_right = st.columns((1.1, 1))
with coef_left:
    st.markdown("**Coefficient review**")
    coef_display = baseline.coefficient_table.copy()
    coef_display = coef_display[coef_display["raw_feature"] != "const"]
    coef_display["coefficient"] = coef_display["coefficient"].map(lambda x: f"{x:,.3f}")
    coef_display["p_value"] = coef_display["p_value"].map(lambda x: f"{x:,.3f}")
    st.dataframe(
        coef_display[["feature", "direction", "coefficient", "p_value"]],
        use_container_width=True,
        hide_index=True,
    )

with coef_right:
    st.markdown("**VIF collinearity scan**")
    vif_display = baseline.vif_table.copy()
    vif_display["vif"] = vif_display["vif"].map(lambda x: f"{x:,.1f}")
    st.dataframe(
        vif_display[["feature", "vif"]].head(12),
        use_container_width=True,
        hide_index=True,
    )

st.info(
    "This baseline is for diagnostic comparison, not final budget allocation. "
    "The next modeling phase should add adstock, saturation, priors, and uncertainty-aware MMM."
)

st.divider()
st.subheader("MMM Foundations")
st.markdown(
    '<p class="mel-caption">Deterministic MMM-style benchmark with channel-specific adstock, '
    "saturation, contribution estimates, and response curves.</p>",
    unsafe_allow_html=True,
)

mmm_result = fit_mmm_foundation_model(df, holdout_weeks=26)
mmm_metric_cols = st.columns(5)
mmm_metric_cols[0].metric("MMM Train R-squared", f"{mmm_result.metrics['train_r_squared']:,.2f}")
mmm_metric_cols[1].metric("MMM Adj. R-squared", f"{mmm_result.metrics['train_adjusted_r_squared']:,.2f}")
mmm_metric_cols[2].metric("MMM Train MAPE", percent(mmm_result.metrics["train_mape"]))
mmm_metric_cols[3].metric("MMM Holdout MAPE", percent(mmm_result.metrics["test_mape"]))
mmm_metric_cols[4].metric("MMM Holdout RMSE", gbp(mmm_result.metrics["test_rmse_gbp"]))

mmm_frame = pd.concat(
    [
        mmm_result.train_frame.assign(sample="Training"),
        mmm_result.test_frame.assign(sample="Holdout"),
    ],
    ignore_index=True,
)

mmm_fit_fig = go.Figure()
mmm_fit_fig.add_trace(
    go.Scatter(
        x=mmm_frame["week_start"],
        y=mmm_frame["revenue_gbp"],
        mode="lines",
        name="Actual revenue",
        line={"color": "#1f2933", "width": 2.4},
    )
)
mmm_fit_fig.add_trace(
    go.Scatter(
        x=mmm_frame["week_start"],
        y=mmm_frame["predicted_revenue_gbp"],
        mode="lines",
        name="MMM foundation prediction",
        line={"color": "#4b6f9c", "width": 2.0},
    )
)
mmm_fit_fig.add_vline(
    x=mmm_result.test_frame["week_start"].min(),
    line_dash="dash",
    line_color="#c65f4b",
    annotation_text="Holdout",
    annotation_position="top left",
)
mmm_fit_fig.update_layout(
    title="Actual vs MMM foundation predicted revenue",
    height=430,
    margin={"l": 12, "r": 12, "t": 48, "b": 24},
    yaxis_title="Revenue GBP",
    xaxis_title=None,
    legend_orientation="h",
    legend_y=1.08,
    plot_bgcolor="#ffffff",
    paper_bgcolor="#ffffff",
)
st.plotly_chart(mmm_fit_fig, use_container_width=True)

contrib_left, contrib_right = st.columns((1, 1))
with contrib_left:
    contribution_fig = px.bar(
        mmm_result.contribution_table,
        x="estimated_contribution_gbp",
        y="channel",
        orientation="h",
        title="Estimated media contribution by channel",
        labels={"estimated_contribution_gbp": "Contribution GBP", "channel": ""},
        color="estimated_roi",
        color_continuous_scale=["#dfe7e2", "#2f7d64"],
    )
    contribution_fig.update_layout(
        height=390,
        margin={"l": 12, "r": 12, "t": 48, "b": 24},
        yaxis={"categoryorder": "total ascending"},
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        coloraxis_showscale=False,
    )
    st.plotly_chart(contribution_fig, use_container_width=True)

with contrib_right:
    response_fig = px.line(
        mmm_result.response_curves,
        x="spend_gbp",
        y="estimated_weekly_contribution_gbp",
        color="channel",
        title="Estimated response curves",
        labels={
            "spend_gbp": "Weekly spend GBP",
            "estimated_weekly_contribution_gbp": "Estimated weekly contribution GBP",
            "channel": "Channel",
        },
        color_discrete_sequence=["#2f7d64", "#4b6f9c", "#c65f4b", "#9a7b3f", "#6b7280", "#7c6aa6"],
    )
    response_fig.update_layout(
        height=390,
        margin={"l": 12, "r": 12, "t": 48, "b": 24},
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        legend_orientation="h",
        legend_y=1.08,
    )
    st.plotly_chart(response_fig, use_container_width=True)

mmm_table_left, mmm_table_right = st.columns((1.2, 1))
with mmm_table_left:
    st.markdown("**Contribution and ROI estimates**")
    contribution_display = mmm_result.contribution_table.copy()
    contribution_display["spend_gbp"] = contribution_display["spend_gbp"].map(gbp)
    contribution_display["estimated_contribution_gbp"] = contribution_display[
        "estimated_contribution_gbp"
    ].map(gbp)
    contribution_display["estimated_roi"] = contribution_display["estimated_roi"].map(x_value)
    contribution_display["contribution_share"] = contribution_display["contribution_share"].map(percent)
    st.dataframe(
        contribution_display[
            ["channel", "spend_gbp", "estimated_contribution_gbp", "estimated_roi", "contribution_share"]
        ],
        use_container_width=True,
        hide_index=True,
    )

with mmm_table_right:
    st.markdown("**Media transformation parameters**")
    parameter_display = mmm_result.parameter_table.copy()
    parameter_display["adstock_decay"] = parameter_display["adstock_decay"].map(lambda x: f"{x:,.2f}")
    parameter_display["half_saturation_gbp"] = parameter_display["half_saturation_gbp"].map(gbp)
    parameter_display["slope"] = parameter_display["slope"].map(lambda x: f"{x:,.2f}")
    st.dataframe(parameter_display, use_container_width=True, hide_index=True)

st.warning(
    "MMM foundations are directional estimates. The next phase should add calibrated parameter search "
    "or Bayesian MMM to estimate uncertainty and improve channel separation."
)

active_mmm_result = mmm_result
active_mmm_label = "MMM foundation"

st.divider()
st.subheader("Calibrated MMM Search")
st.markdown(
    '<p class="mel-caption">Optional time-aware search over adstock and saturation assumptions. '
    "Use this as a bridge toward Bayesian MMM, not as final uncertainty modeling.</p>",
    unsafe_allow_html=True,
)

run_calibration = st.checkbox("Run calibrated parameter search", value=False)
if run_calibration:
    with st.spinner("Calibrating MMM parameters..."):
        calibration = calibrate_mmm_parameters(df, holdout_weeks=26, validation_weeks=20)

    calibration_metrics = pd.DataFrame(
        [
            {
                "model": "Fixed MMM",
                "train_r_squared": mmm_result.metrics["train_r_squared"],
                "holdout_mape": mmm_result.metrics["test_mape"],
                "holdout_rmse_gbp": mmm_result.metrics["test_rmse_gbp"],
            },
            {
                "model": "Calibrated MMM",
                "train_r_squared": calibration.mmm_result.metrics["train_r_squared"],
                "holdout_mape": calibration.mmm_result.metrics["test_mape"],
                "holdout_rmse_gbp": calibration.mmm_result.metrics["test_rmse_gbp"],
            },
        ]
    )
    calibration_display = calibration_metrics.copy()
    calibration_display["train_r_squared"] = calibration_display["train_r_squared"].map(
        lambda x: f"{x:,.2f}"
    )
    calibration_display["holdout_mape"] = calibration_display["holdout_mape"].map(percent)
    calibration_display["holdout_rmse_gbp"] = calibration_display["holdout_rmse_gbp"].map(gbp)
    st.dataframe(calibration_display, use_container_width=True, hide_index=True)

    cal_left, cal_right = st.columns((1, 1))
    with cal_left:
        st.markdown("**Calibrated parameters**")
        calibrated_params = calibration.mmm_result.parameter_table.copy()
        calibrated_params["adstock_decay"] = calibrated_params["adstock_decay"].map(
            lambda x: f"{x:,.2f}"
        )
        calibrated_params["half_saturation_gbp"] = calibrated_params["half_saturation_gbp"].map(gbp)
        calibrated_params["slope"] = calibrated_params["slope"].map(lambda x: f"{x:,.2f}")
        st.dataframe(calibrated_params, use_container_width=True, hide_index=True)

    with cal_right:
        st.markdown("**Best validation candidates by channel**")
        best_rows = (
            calibration.search_table.sort_values("validation_mape")
            .groupby("channel", as_index=False)
            .first()
            .sort_values("channel")
        )
        best_display = best_rows[
            ["channel", "adstock_decay", "half_saturation_gbp", "validation_mape"]
        ].copy()
        best_display["adstock_decay"] = best_display["adstock_decay"].map(lambda x: f"{x:,.2f}")
        best_display["half_saturation_gbp"] = best_display["half_saturation_gbp"].map(gbp)
        best_display["validation_mape"] = best_display["validation_mape"].map(percent)
        st.dataframe(best_display, use_container_width=True, hide_index=True)

    use_calibrated_for_planner = st.checkbox(
        "Use calibrated MMM for budget planner",
        value=True,
    )
    if use_calibrated_for_planner:
        active_mmm_result = calibration.mmm_result
        active_mmm_label = "calibrated MMM"
else:
    st.info("Calibration is optional. Run it when you want to compare fixed assumptions with tuned parameters.")

st.divider()
st.subheader("MMM Uncertainty Intervals")
st.markdown(
    '<p class="mel-caption">Coefficient simulation around the active MMM model. These intervals are '
    "not Bayesian posteriors, but they make model uncertainty visible for planning.</p>",
    unsafe_allow_html=True,
)

draw_count = st.slider("Uncertainty simulation draws", 100, 1000, 500, 100)
uncertainty = simulate_mmm_uncertainty(active_mmm_result, draws=draw_count, seed=42)

uncertainty_left, uncertainty_right = st.columns((1.1, 1))
with uncertainty_left:
    interval_fig = go.Figure()
    interval_df = uncertainty.contribution_intervals.sort_values("contribution_mean_gbp")
    interval_fig.add_trace(
        go.Bar(
            x=interval_df["contribution_mean_gbp"],
            y=interval_df["channel"],
            orientation="h",
            name="Mean contribution",
            marker={"color": "#2f7d64"},
            error_x={
                "type": "data",
                "symmetric": False,
                "array": interval_df["contribution_upper_gbp"] - interval_df["contribution_mean_gbp"],
                "arrayminus": interval_df["contribution_mean_gbp"] - interval_df["contribution_lower_gbp"],
            },
        )
    )
    interval_fig.update_layout(
        title="Estimated contribution intervals by channel",
        height=410,
        margin={"l": 12, "r": 12, "t": 48, "b": 24},
        xaxis_title="Contribution GBP",
        yaxis_title=None,
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        showlegend=False,
    )
    st.plotly_chart(interval_fig, use_container_width=True)

with uncertainty_right:
    prediction_fig = go.Figure()
    prediction_df = uncertainty.prediction_intervals.copy()
    prediction_fig.add_trace(
        go.Scatter(
            x=prediction_df["week_start"],
            y=prediction_df["prediction_upper_gbp"],
            mode="lines",
            line={"width": 0},
            showlegend=False,
            hoverinfo="skip",
        )
    )
    prediction_fig.add_trace(
        go.Scatter(
            x=prediction_df["week_start"],
            y=prediction_df["prediction_lower_gbp"],
            mode="lines",
            fill="tonexty",
            fillcolor="rgba(47, 125, 100, 0.18)",
            line={"width": 0},
            name="Interval",
        )
    )
    prediction_fig.add_trace(
        go.Scatter(
            x=prediction_df["week_start"],
            y=prediction_df["revenue_gbp"],
            mode="lines+markers",
            name="Actual holdout",
            line={"color": "#1f2933", "width": 2},
        )
    )
    prediction_fig.add_trace(
        go.Scatter(
            x=prediction_df["week_start"],
            y=prediction_df["prediction_mean_gbp"],
            mode="lines",
            name="Mean prediction",
            line={"color": "#2f7d64", "width": 2},
        )
    )
    prediction_fig.update_layout(
        title="Holdout prediction interval",
        height=410,
        margin={"l": 12, "r": 12, "t": 48, "b": 24},
        yaxis_title="Revenue GBP",
        xaxis_title=None,
        legend_orientation="h",
        legend_y=1.08,
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
    )
    st.plotly_chart(prediction_fig, use_container_width=True)

uncertainty_display = uncertainty.contribution_intervals.copy()
for money_col in [
    "contribution_mean_gbp",
    "contribution_lower_gbp",
    "contribution_upper_gbp",
]:
    uncertainty_display[money_col] = uncertainty_display[money_col].map(gbp)
for roi_col in ["roi_mean", "roi_lower", "roi_upper"]:
    uncertainty_display[roi_col] = uncertainty_display[roi_col].map(x_value)
st.dataframe(
    uncertainty_display[
        [
            "channel",
            "contribution_mean_gbp",
            "contribution_lower_gbp",
            "contribution_upper_gbp",
            "roi_mean",
            "roi_lower",
            "roi_upper",
        ]
    ],
    use_container_width=True,
    hide_index=True,
)

st.divider()
st.subheader("Incrementality Calibration")
st.markdown(
    '<p class="mel-caption">Bridge MMM estimates with experiment evidence. '
    "The demo readouts mimic geo holdouts and lift tests that a commercial analytics team would use "
    "to calibrate channel contribution.</p>",
    unsafe_allow_html=True,
)

demo_lift_tests = demo_lift_test_calibrations(active_mmm_result)
evidence_source = st.radio(
    "Experiment evidence",
    ["Demo lift tests", "Upload lift-test CSV"],
    horizontal=True,
)
st.download_button(
    "Download lift-test template",
    data=lift_test_template_csv(),
    file_name="incrementality_lift_tests_template.csv",
    mime="text/csv",
)

lift_tests = demo_lift_tests
evidence_label = "Demo lift-test evidence"
if evidence_source == "Upload lift-test CSV":
    uploaded_lift_tests = st.file_uploader(
        "Upload incrementality lift-test CSV",
        type=["csv"],
        key="lift_test_csv_upload",
    )
    if uploaded_lift_tests is None:
        st.info("Upload a lift-test CSV to replace the demo evidence.")
    else:
        lift_csv_text = uploaded_lift_tests.getvalue().decode("utf-8-sig")
        parsed_lift_tests, lift_errors = validate_lift_test_csv_text(lift_csv_text)
        if lift_errors or parsed_lift_tests is None:
            st.error("Uploaded lift-test CSV failed validation. Demo evidence remains active.")
            for error in lift_errors:
                st.write(f"- {error}")
        else:
            lift_tests = parsed_lift_tests
            evidence_label = uploaded_lift_tests.name
            st.success(f"Loaded {len(lift_tests):,} lift-test rows from {uploaded_lift_tests.name}.")

evidence_quality = assess_lift_test_evidence(lift_tests)
use_approved_only = st.checkbox("Use only approved evidence for calibration", value=True)
calibration_lift_tests = approved_lift_tests(lift_tests) if use_approved_only else lift_tests
if calibration_lift_tests.empty:
    st.warning("No approved evidence is available for calibration. Review approval statuses or disable the filter.")
    lift_factor_table = calibration_factors(lift_tests)
else:
    lift_factor_table = calibration_factors(calibration_lift_tests)
apply_incrementality_calibration = st.checkbox(
    "Apply selected lift-test calibration",
    value=False,
    disabled=calibration_lift_tests.empty,
)
st.caption(f"Active experiment evidence: {evidence_label}.")

calibration_left, calibration_right = st.columns((1.05, 1))
with calibration_left:
    st.markdown("**Evidence quality review**")
    lift_display = evidence_quality.copy()
    for money_col in [
        "model_lift_gbp",
        "observed_lift_gbp",
        "observed_lift_lower_gbp",
        "observed_lift_upper_gbp",
    ]:
        lift_display[money_col] = lift_display[money_col].map(gbp)
    lift_display["calibration_factor"] = lift_display["calibration_factor"].map(x_value)
    lift_display_columns = [
        column
        for column in [
            "test_name",
            "channel",
            "experiment_type",
            "start_date",
            "end_date",
            "weeks",
            "market",
            "model_lift_gbp",
            "observed_lift_gbp",
            "calibration_factor",
            "approval_status",
            "evidence_quality_score",
            "quality_tier",
            "review_flags",
        ]
        if column in lift_display.columns
    ]
    st.dataframe(
        lift_display[lift_display_columns],
        use_container_width=True,
        hide_index=True,
    )

with calibration_right:
    factor_fig = px.bar(
        lift_factor_table.sort_values("calibration_factor"),
        x="calibration_factor",
        y="channel",
        orientation="h",
        title="Experiment calibration factors",
        labels={"calibration_factor": "Observed / MMM lift", "channel": ""},
        color="calibration_factor",
        color_continuous_scale=["#c65f4b", "#f7f7f7", "#2f7d64"],
        range_color=[0.5, 1.5],
    )
    factor_fig.add_vline(x=1.0, line_dash="dash", line_color="#1f2933")
    factor_fig.update_layout(
        height=330,
        margin={"l": 12, "r": 12, "t": 48, "b": 24},
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        coloraxis_showscale=False,
    )
    st.plotly_chart(factor_fig, use_container_width=True)

if apply_incrementality_calibration:
    calibrated_contribution = apply_lift_calibration(
        active_mmm_result.contribution_table,
        calibration_lift_tests,
    )
    calibrated_intervals = apply_lift_calibration_to_intervals(uncertainty, calibration_lift_tests)

    calibrated_left, calibrated_right = st.columns((1, 1))
    with calibrated_left:
        calibrated_fig = px.bar(
            calibrated_contribution.sort_values("estimated_contribution_calibrated_gbp"),
            x="estimated_contribution_calibrated_gbp",
            y="channel",
            orientation="h",
            title="Experiment-calibrated contribution",
            labels={"estimated_contribution_calibrated_gbp": "Contribution GBP", "channel": ""},
            color="estimated_roi_calibrated",
            color_continuous_scale=["#dfe7e2", "#2f7d64"],
        )
        calibrated_fig.update_layout(
            height=380,
            margin={"l": 12, "r": 12, "t": 48, "b": 24},
            plot_bgcolor="#ffffff",
            paper_bgcolor="#ffffff",
            coloraxis_showscale=False,
        )
        st.plotly_chart(calibrated_fig, use_container_width=True)

    with calibrated_right:
        calibrated_interval_display = calibrated_intervals.copy()
        for money_col in [
            "contribution_mean_calibrated_gbp",
            "contribution_lower_calibrated_gbp",
            "contribution_upper_calibrated_gbp",
        ]:
            calibrated_interval_display[money_col] = calibrated_interval_display[money_col].map(gbp)
        calibrated_interval_display["roi_mean_calibrated"] = calibrated_interval_display[
            "roi_mean_calibrated"
        ].map(x_value)
        st.markdown("**Calibrated uncertainty view**")
        st.dataframe(
            calibrated_interval_display[
                [
                    "channel",
                    "calibration_status",
                    "contribution_mean_calibrated_gbp",
                    "contribution_lower_calibrated_gbp",
                    "contribution_upper_calibrated_gbp",
                    "roi_mean_calibrated",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

    calibrated_display = calibrated_contribution.copy()
    for money_col in [
        "spend_gbp",
        "estimated_contribution_gbp",
        "estimated_contribution_calibrated_gbp",
    ]:
        calibrated_display[money_col] = calibrated_display[money_col].map(gbp)
    for roi_col in ["estimated_roi", "estimated_roi_calibrated", "calibration_factor"]:
        calibrated_display[roi_col] = calibrated_display[roi_col].map(x_value)
    st.dataframe(
        calibrated_display[
            [
                "channel",
                "calibration_status",
                "spend_gbp",
                "estimated_contribution_gbp",
                "estimated_contribution_calibrated_gbp",
                "estimated_roi",
                "estimated_roi_calibrated",
                "calibration_factor",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info(
        "Lift-test evidence is loaded for review. Enable calibration to show adjusted contribution, "
        "ROI, and uncertainty intervals."
    )

st.caption(
    "This calibration layer is diagnostic. The current budget planner still uses the active MMM response curves; "
    "future phases can feed experiment-calibrated priors into Bayesian MMM."
)

st.divider()
st.subheader("Bayesian MMM Foundations")
st.markdown(
    '<p class="mel-caption">Posterior layer over the active MMM design matrix. '
    "Approved lift-test evidence can inform media priors before drawing posterior contribution "
    "and predictive intervals.</p>",
    unsafe_allow_html=True,
)

bayesian_left_control, bayesian_right_control = st.columns((1, 1))
with bayesian_left_control:
    bayesian_draws = st.slider("Bayesian posterior draws", 100, 1200, 600, 100)
with bayesian_right_control:
    use_experiment_priors = st.checkbox(
        "Use selected experiment evidence as Bayesian priors",
        value=True,
        disabled=calibration_lift_tests.empty,
    )

bayesian_lift_tests = (
    calibration_lift_tests if use_experiment_priors and not calibration_lift_tests.empty else None
)
bayesian_result = fit_bayesian_mmm(
    active_mmm_result,
    lift_tests=bayesian_lift_tests,
    draws=bayesian_draws,
    seed=42,
)

bayes_metric_cols = st.columns(5)
bayes_metric_cols[0].metric("Posterior draws", integer(bayesian_result.diagnostics["draw_count"]))
bayes_metric_cols[1].metric(
    "Holdout coverage",
    percent(bayesian_result.diagnostics["holdout_coverage"]),
)
bayes_metric_cols[2].metric(
    "Posterior MAPE",
    percent(bayesian_result.diagnostics["holdout_mape"]),
)
bayes_metric_cols[3].metric(
    "Posterior sigma",
    gbp(bayesian_result.diagnostics["posterior_sigma_mean_gbp"]),
)
bayes_metric_cols[4].metric(
    "Experiment priors",
    integer(bayesian_result.diagnostics["experiment_informed_priors"]),
)

bayesian_left, bayesian_right = st.columns((1.1, 1))
with bayesian_left:
    bayesian_contribution_df = bayesian_result.contribution_intervals.sort_values(
        "contribution_mean_gbp"
    )
    bayesian_interval_fig = go.Figure()
    bayesian_interval_fig.add_trace(
        go.Bar(
            x=bayesian_contribution_df["contribution_mean_gbp"],
            y=bayesian_contribution_df["channel"],
            orientation="h",
            name="Posterior mean",
            marker={"color": "#4b6f9c"},
            error_x={
                "type": "data",
                "symmetric": False,
                "array": bayesian_contribution_df["contribution_upper_gbp"]
                - bayesian_contribution_df["contribution_mean_gbp"],
                "arrayminus": bayesian_contribution_df["contribution_mean_gbp"]
                - bayesian_contribution_df["contribution_lower_gbp"],
            },
        )
    )
    bayesian_interval_fig.update_layout(
        title="Bayesian contribution posterior intervals",
        height=410,
        margin={"l": 12, "r": 12, "t": 48, "b": 24},
        xaxis_title="Contribution GBP",
        yaxis_title=None,
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        showlegend=False,
    )
    st.plotly_chart(bayesian_interval_fig, use_container_width=True)

with bayesian_right:
    bayesian_prediction = bayesian_result.prediction_intervals.copy()
    bayesian_prediction_fig = go.Figure()
    bayesian_prediction_fig.add_trace(
        go.Scatter(
            x=bayesian_prediction["week_start"],
            y=bayesian_prediction["posterior_prediction_upper_gbp"],
            mode="lines",
            line={"width": 0},
            showlegend=False,
            hoverinfo="skip",
        )
    )
    bayesian_prediction_fig.add_trace(
        go.Scatter(
            x=bayesian_prediction["week_start"],
            y=bayesian_prediction["posterior_prediction_lower_gbp"],
            mode="lines",
            fill="tonexty",
            fillcolor="rgba(75, 111, 156, 0.18)",
            line={"width": 0},
            name="Posterior interval",
        )
    )
    bayesian_prediction_fig.add_trace(
        go.Scatter(
            x=bayesian_prediction["week_start"],
            y=bayesian_prediction["revenue_gbp"],
            mode="lines+markers",
            name="Actual holdout",
            line={"color": "#1f2933", "width": 2},
        )
    )
    bayesian_prediction_fig.add_trace(
        go.Scatter(
            x=bayesian_prediction["week_start"],
            y=bayesian_prediction["posterior_prediction_mean_gbp"],
            mode="lines",
            name="Posterior mean",
            line={"color": "#4b6f9c", "width": 2},
        )
    )
    bayesian_prediction_fig.update_layout(
        title="Bayesian holdout posterior predictive interval",
        height=410,
        margin={"l": 12, "r": 12, "t": 48, "b": 24},
        yaxis_title="Revenue GBP",
        xaxis_title=None,
        legend_orientation="h",
        legend_y=1.08,
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
    )
    st.plotly_chart(bayesian_prediction_fig, use_container_width=True)

bayesian_tables_left, bayesian_tables_right = st.columns((1.1, 1))
with bayesian_tables_left:
    bayesian_display = bayesian_result.contribution_intervals.copy()
    for money_col in [
        "contribution_mean_gbp",
        "contribution_lower_gbp",
        "contribution_upper_gbp",
    ]:
        bayesian_display[money_col] = bayesian_display[money_col].map(gbp)
    for roi_col in ["roi_mean", "roi_lower", "roi_upper"]:
        bayesian_display[roi_col] = bayesian_display[roi_col].map(x_value)
    st.markdown("**Bayesian contribution table**")
    st.dataframe(
        bayesian_display[
            [
                "channel",
                "prior_source",
                "contribution_mean_gbp",
                "contribution_lower_gbp",
                "contribution_upper_gbp",
                "roi_mean",
                "roi_lower",
                "roi_upper",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

with bayesian_tables_right:
    media_prior_display = bayesian_result.coefficient_summary[
        bayesian_result.coefficient_summary["channel"] != ""
    ].copy()
    media_prior_display["prior_mean"] = media_prior_display["prior_mean"].map(lambda x: f"{x:,.0f}")
    media_prior_display["posterior_mean"] = media_prior_display["posterior_mean"].map(
        lambda x: f"{x:,.0f}"
    )
    media_prior_display["probability_positive"] = media_prior_display["probability_positive"].map(
        percent
    )
    st.markdown("**Media coefficient priors**")
    st.dataframe(
        media_prior_display[
            [
                "channel",
                "prior_source",
                "prior_mean",
                "posterior_mean",
                "probability_positive",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

st.info(
    "This Bayesian layer samples coefficients and residual variance for the active transformed MMM "
    "features. It is a posterior foundation, not yet a full Bayesian sampler over adstock and "
    "saturation parameters."
)

st.divider()
st.subheader("Budget Scenario Planner")
st.markdown(
    '<p class="mel-caption">Compare current weekly spend with a proposed allocation using the '
    f"{active_mmm_label} response curves.</p>",
    unsafe_allow_html=True,
)

planner_left, planner_right = st.columns((0.9, 1.25))
with planner_left:
    lookback_weeks = st.slider(
        "Current spend lookback",
        4,
        26,
        13,
        help="Latest weeks used to estimate current weekly spend.",
    )
    current_spend = current_weekly_spend(df, lookback_weeks=lookback_weeks)
    current_total_budget = sum(current_spend.values())
    budget_multiplier = st.slider("Weekly budget multiplier", 0.70, 1.30, 1.00, 0.05)
    gross_margin_rate = st.slider(
        "Gross margin assumption",
        0.20,
        0.80,
        0.52,
        0.01,
        format="%.2f",
    )
    proposed_total_budget = current_total_budget * budget_multiplier
    allocation_profile = st.radio(
        "Allocation profile",
        ["Current mix", "ROI-weighted tilt", "Optimized allocation", "Manual shares"],
        horizontal=False,
    )

    if allocation_profile == "ROI-weighted tilt":
        tilt_strength = st.slider("ROI tilt strength", 0.10, 1.50, 0.60, 0.10)
        proposed_spend = roi_weighted_allocation(
            current_spend,
            active_mmm_result,
            proposed_total_budget,
            tilt_strength=tilt_strength,
        )
        optimization_result = None
    elif allocation_profile == "Optimized allocation":
        if optimize_budget_allocation is None:
            st.warning("The optimizer is unavailable while the app environment refreshes.")
            proposed_spend = allocation_from_shares(
                current_spend,
                {column: spend for column, spend in current_spend.items()},
                proposed_total_budget,
            )
            optimization_result = None
        else:
            optimization_objective_label = st.radio(
                "Optimization objective",
                ["Profit after media", "Contribution revenue"],
                horizontal=False,
            )
            min_channel_share = st.slider("Minimum channel share", 0.00, 0.15, 0.02, 0.01)
            max_channel_share = st.slider("Maximum channel share", 0.20, 0.70, 0.45, 0.01)
            optimization_objective = (
                "profit"
                if optimization_objective_label == "Profit after media"
                else "contribution"
            )
            try:
                optimization_result = optimize_budget_allocation(
                    current_spend,
                    active_mmm_result,
                    proposed_total_budget,
                    objective=optimization_objective,
                    gross_margin_rate=gross_margin_rate,
                    min_share=min_channel_share,
                    max_share=max_channel_share,
                )
                proposed_spend = optimization_result.allocation
            except ValueError as exc:
                st.error(str(exc))
                st.stop()
    elif allocation_profile == "Manual shares":
        st.markdown("**Manual channel shares**")
        current_shares = {
            column: spend / current_total_budget if current_total_budget else 0.0
            for column, spend in current_spend.items()
        }
        manual_shares = {}
        for column, label in CHANNEL_LABELS.items():
            manual_shares[column] = st.slider(
                label,
                0.0,
                0.60,
                float(current_shares[column]),
                0.01,
                format="%.2f",
            )
        proposed_spend = allocation_from_shares(current_spend, manual_shares, proposed_total_budget)
        st.caption("Manual shares are normalized to sum to 100%.")
        optimization_result = None
    else:
        proposed_spend = allocation_from_shares(
            current_spend,
            {column: spend for column, spend in current_spend.items()},
            proposed_total_budget,
        )
        optimization_result = None

scenario = evaluate_budget_scenario(
    df,
    active_mmm_result,
    proposed_spend,
    lookback_weeks=lookback_weeks,
    gross_margin_rate=gross_margin_rate,
)

with planner_right:
    scenario_cols = st.columns(5)
    scenario_cols[0].metric("Current weekly spend", gbp(scenario.summary["current_weekly_spend_gbp"]))
    scenario_cols[1].metric("Proposed weekly spend", gbp(scenario.summary["proposed_weekly_spend_gbp"]))
    scenario_cols[2].metric("Est. contribution lift", gbp(scenario.summary["weekly_contribution_change_gbp"]))
    scenario_cols[3].metric("Est. profit lift", gbp(scenario.summary["weekly_profit_change_gbp"]))
    scenario_cols[4].metric("Profit ROI", x_value(scenario.summary["proposed_profit_roi"]))

    scenario_chart_df = scenario.channel_table.copy()
    scenario_chart = px.bar(
        scenario_chart_df,
        x="channel",
        y=["current_weekly_spend_gbp", "proposed_weekly_spend_gbp"],
        barmode="group",
        title="Current vs proposed weekly spend",
        labels={"value": "Weekly spend GBP", "channel": "", "variable": "Scenario"},
        color_discrete_sequence=["#6b7280", "#2f7d64"],
    )
    scenario_chart.update_layout(
        height=360,
        margin={"l": 12, "r": 12, "t": 48, "b": 24},
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        legend_orientation="h",
        legend_y=1.08,
    )
    scenario_chart.for_each_trace(
        lambda trace: trace.update(
            name={
                "current_weekly_spend_gbp": "Current",
                "proposed_weekly_spend_gbp": "Proposed",
            }.get(trace.name, trace.name)
        )
    )
    st.plotly_chart(scenario_chart, use_container_width=True)

scenario_display = scenario.channel_table.copy()
for money_col in [
    "current_weekly_spend_gbp",
    "proposed_weekly_spend_gbp",
    "weekly_spend_change_gbp",
    "proposed_weekly_contribution_gbp",
    "weekly_contribution_change_gbp",
    "proposed_weekly_profit_after_media_gbp",
    "weekly_profit_change_gbp",
]:
    scenario_display[money_col] = scenario_display[money_col].map(gbp)
for roi_col in ["proposed_roi", "proposed_profit_roi"]:
    scenario_display[roi_col] = scenario_display[roi_col].map(x_value)
for roi_col in ["incremental_roi", "incremental_profit_roi"]:
    scenario_display[roi_col] = scenario_display[roi_col].map(
        lambda value: "n/a" if pd.isna(value) else x_value(value)
    )
st.dataframe(
    scenario_display[
        [
            "channel",
            "current_weekly_spend_gbp",
            "proposed_weekly_spend_gbp",
            "weekly_spend_change_gbp",
            "proposed_weekly_contribution_gbp",
            "weekly_contribution_change_gbp",
            "proposed_weekly_profit_after_media_gbp",
            "weekly_profit_change_gbp",
            "proposed_roi",
            "incremental_roi",
            "proposed_profit_roi",
            "incremental_profit_roi",
        ]
    ],
    use_container_width=True,
    hide_index=True,
)

st.info(
    f"Scenario planning uses deterministic response curves from the {active_mmm_label} model. "
    f"Profit metrics assume a {gross_margin_rate * 100:,.0f}% gross margin. "
    "It is suitable for directional planning, not final budget approval."
)

if optimization_result is not None:
    st.markdown("**Optimization diagnostics**")
    opt_diag = optimization_result.diagnostics.copy()
    for money_col in [
        "current_mix_weekly_spend_gbp",
        "optimized_weekly_spend_gbp",
        "min_weekly_spend_gbp",
        "max_weekly_spend_gbp",
        "current_mix_objective_gbp",
        "optimized_objective_gbp",
        "objective_lift_gbp",
    ]:
        opt_diag[money_col] = opt_diag[money_col].map(gbp)
    opt_diag["optimized_share"] = opt_diag["optimized_share"].map(percent)
    st.dataframe(
        opt_diag[
            [
                "channel",
                "optimized_share",
                "current_mix_weekly_spend_gbp",
                "optimized_weekly_spend_gbp",
                "objective_lift_gbp",
                "constraint_status",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )
    st.caption(
        "The optimizer uses greedy marginal response steps with min/max channel share constraints. "
        "It is designed for transparent directional planning."
    )

st.divider()
st.subheader("Executive Summary Draft")
executive_summary = build_executive_summary(kpis, active_mmm_result, scenario)
st.markdown(f"**{executive_summary.headline}**")

summary_cols = st.columns((1.2, 1))
with summary_cols[0]:
    st.markdown("**Highlights**")
    for highlight in executive_summary.highlights:
        st.write(f"- {highlight}")

with summary_cols[1]:
    st.markdown("**Recommendation**")
    st.write(executive_summary.recommendation)

with st.expander("Caveats for stakeholder communication"):
    for caveat in executive_summary.caveats:
        st.write(f"- {caveat}")
