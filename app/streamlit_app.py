from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

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
from marketing_effectiveness_lab.data.generator import generate_and_validate
from marketing_effectiveness_lab.data.schema import validate_weekly_dataset


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "demo" / "fashion_retail_weekly.csv"
DEMO_OUTPUT_DIR = PROJECT_ROOT / "data" / "demo"

PAGE_TITLE = "Marketing Effectiveness Lab"


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


@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
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


df = load_data()
selected_df = filtered_frame(df)
selected_channels = selected_df.attrs["channels"]
show_promotions = selected_df.attrs["show_promotions"]

st.title(PAGE_TITLE)
st.markdown(
    '<p class="mel-caption">Analyst dashboard for UK fashion ecommerce marketing performance, '
    "MMM readiness, and commercial diagnostics.</p>",
    unsafe_allow_html=True,
)

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

