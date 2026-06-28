"""Connector template helpers for common marketing and commerce exports."""

from __future__ import annotations

from dataclasses import dataclass
from io import StringIO

import pandas as pd


@dataclass(frozen=True)
class ConnectorColumn:
    name: str
    description: str
    required: bool = True
    non_negative: bool = True
    date_like: bool = False


@dataclass(frozen=True)
class ConnectorSpec:
    key: str
    label: str
    description: str
    columns: tuple[ConnectorColumn, ...]
    sample_rows: tuple[dict[str, object], ...]


CONNECTOR_SPECS: tuple[ConnectorSpec, ...] = (
    ConnectorSpec(
        key="ga4",
        label="GA4 traffic and conversion export",
        description="Weekly web analytics export for sessions, users, purchases, and revenue.",
        columns=(
            ConnectorColumn("week_start", "Monday date for the reporting week.", non_negative=False, date_like=True),
            ConnectorColumn("session_source_medium", "GA4 source / medium value.", non_negative=False),
            ConnectorColumn("sessions", "Weekly sessions."),
            ConnectorColumn("total_users", "Weekly users."),
            ConnectorColumn("new_users", "Weekly new users."),
            ConnectorColumn("purchases", "Weekly ecommerce purchases."),
            ConnectorColumn("purchase_revenue_gbp", "Weekly purchase revenue in GBP."),
        ),
        sample_rows=(
            {
                "week_start": "2025-01-06",
                "session_source_medium": "google / organic",
                "sessions": 145000,
                "total_users": 92000,
                "new_users": 41000,
                "purchases": 6100,
                "purchase_revenue_gbp": 525000,
            },
            {
                "week_start": "2025-01-06",
                "session_source_medium": "newsletter / email",
                "sessions": 26000,
                "total_users": 21000,
                "new_users": 4000,
                "purchases": 2200,
                "purchase_revenue_gbp": 188000,
            },
        ),
    ),
    ConnectorSpec(
        key="google_ads",
        label="Google Ads weekly export",
        description="Weekly paid search export for spend, clicks, impressions, and conversions.",
        columns=(
            ConnectorColumn("week_start", "Monday date for the reporting week.", non_negative=False, date_like=True),
            ConnectorColumn("campaign_name", "Google Ads campaign name.", non_negative=False),
            ConnectorColumn("campaign_type", "Search, Performance Max, Shopping, or other type.", non_negative=False),
            ConnectorColumn("cost_gbp", "Weekly media cost in GBP."),
            ConnectorColumn("impressions", "Weekly impressions."),
            ConnectorColumn("clicks", "Weekly clicks."),
            ConnectorColumn("conversions", "Weekly platform conversions."),
            ConnectorColumn("conversion_value_gbp", "Weekly conversion value in GBP."),
        ),
        sample_rows=(
            {
                "week_start": "2025-01-06",
                "campaign_name": "UK Brand Search",
                "campaign_type": "Search",
                "cost_gbp": 42000,
                "impressions": 880000,
                "clicks": 76000,
                "conversions": 5200,
                "conversion_value_gbp": 448000,
            },
            {
                "week_start": "2025-01-06",
                "campaign_name": "UK Nonbrand Dresses",
                "campaign_type": "Search",
                "cost_gbp": 31000,
                "impressions": 640000,
                "clicks": 39000,
                "conversions": 2100,
                "conversion_value_gbp": 180000,
            },
        ),
    ),
    ConnectorSpec(
        key="meta_ads",
        label="Meta Ads weekly export",
        description="Weekly paid social export for spend, reach, impressions, clicks, and purchases.",
        columns=(
            ConnectorColumn("week_start", "Monday date for the reporting week.", non_negative=False, date_like=True),
            ConnectorColumn("campaign_name", "Meta campaign name.", non_negative=False),
            ConnectorColumn("objective", "Campaign objective.", non_negative=False),
            ConnectorColumn("spend_gbp", "Weekly media spend in GBP."),
            ConnectorColumn("reach", "Weekly reach."),
            ConnectorColumn("impressions", "Weekly impressions."),
            ConnectorColumn("link_clicks", "Weekly link clicks."),
            ConnectorColumn("purchases", "Weekly attributed purchases."),
            ConnectorColumn("purchase_value_gbp", "Weekly attributed purchase value in GBP."),
        ),
        sample_rows=(
            {
                "week_start": "2025-01-06",
                "campaign_name": "UK Prospecting Broad",
                "objective": "Sales",
                "spend_gbp": 55000,
                "reach": 810000,
                "impressions": 2100000,
                "link_clicks": 47000,
                "purchases": 2500,
                "purchase_value_gbp": 215000,
            },
            {
                "week_start": "2025-01-06",
                "campaign_name": "UK Retargeting",
                "objective": "Sales",
                "spend_gbp": 18000,
                "reach": 240000,
                "impressions": 710000,
                "link_clicks": 19000,
                "purchases": 1700,
                "purchase_value_gbp": 146000,
            },
        ),
    ),
    ConnectorSpec(
        key="shopify",
        label="Shopify or ecommerce orders export",
        description="Weekly order and revenue export for ecommerce outcome reconciliation.",
        columns=(
            ConnectorColumn("week_start", "Monday date for the reporting week.", non_negative=False, date_like=True),
            ConnectorColumn("gross_sales_gbp", "Weekly gross sales in GBP."),
            ConnectorColumn("discounts_gbp", "Weekly discounts in GBP."),
            ConnectorColumn("returns_gbp", "Weekly returns or refunds in GBP."),
            ConnectorColumn("net_sales_gbp", "Weekly net sales in GBP."),
            ConnectorColumn("orders", "Weekly order count."),
            ConnectorColumn("new_customer_orders", "Weekly new-customer orders."),
            ConnectorColumn("average_order_value_gbp", "Weekly average order value in GBP."),
        ),
        sample_rows=(
            {
                "week_start": "2025-01-06",
                "gross_sales_gbp": 1250000,
                "discounts_gbp": 110000,
                "returns_gbp": 85000,
                "net_sales_gbp": 1055000,
                "orders": 12600,
                "new_customer_orders": 5400,
                "average_order_value_gbp": 83.7,
            },
            {
                "week_start": "2025-01-13",
                "gross_sales_gbp": 1180000,
                "discounts_gbp": 92000,
                "returns_gbp": 78000,
                "net_sales_gbp": 1010000,
                "orders": 11900,
                "new_customer_orders": 5000,
                "average_order_value_gbp": 84.9,
            },
        ),
    ),
    ConnectorSpec(
        key="crm",
        label="CRM and lifecycle export",
        description="Weekly email or lifecycle marketing export for send volume, cost, and revenue.",
        columns=(
            ConnectorColumn("week_start", "Monday date for the reporting week.", non_negative=False, date_like=True),
            ConnectorColumn("campaign_group", "Campaign group or lifecycle programme.", non_negative=False),
            ConnectorColumn("sends", "Weekly sends."),
            ConnectorColumn("delivered", "Weekly delivered messages."),
            ConnectorColumn("opens", "Weekly opens."),
            ConnectorColumn("clicks", "Weekly clicks."),
            ConnectorColumn("orders", "Weekly attributed orders."),
            ConnectorColumn("revenue_gbp", "Weekly attributed revenue in GBP."),
            ConnectorColumn("cost_gbp", "Weekly platform, agency, or incentive cost in GBP."),
        ),
        sample_rows=(
            {
                "week_start": "2025-01-06",
                "campaign_group": "Newsletter",
                "sends": 780000,
                "delivered": 760000,
                "opens": 320000,
                "clicks": 44000,
                "orders": 2100,
                "revenue_gbp": 178000,
                "cost_gbp": 4500,
            },
            {
                "week_start": "2025-01-06",
                "campaign_group": "Abandoned basket",
                "sends": 95000,
                "delivered": 91000,
                "opens": 51000,
                "clicks": 13500,
                "orders": 980,
                "revenue_gbp": 83000,
                "cost_gbp": 1200,
            },
        ),
    ),
    ConnectorSpec(
        key="display_ads",
        label="Display ads weekly export",
        description="Weekly display media export for programmatic or publisher display investment.",
        columns=(
            ConnectorColumn("week_start", "Monday date for the reporting week.", non_negative=False, date_like=True),
            ConnectorColumn("campaign_name", "Display campaign or insertion-order name.", non_negative=False),
            ConnectorColumn("publisher_or_platform", "DSP, publisher, or network name.", non_negative=False),
            ConnectorColumn("spend_gbp", "Weekly display media spend in GBP."),
            ConnectorColumn("impressions", "Weekly display impressions."),
            ConnectorColumn("clicks", "Weekly display clicks."),
            ConnectorColumn("view_through_conversions", "Weekly view-through conversions."),
            ConnectorColumn("click_through_conversions", "Weekly click-through conversions."),
        ),
        sample_rows=(
            {
                "week_start": "2025-01-06",
                "campaign_name": "UK Display Prospecting",
                "publisher_or_platform": "Programmatic DSP",
                "spend_gbp": 16500,
                "impressions": 1850000,
                "clicks": 9200,
                "view_through_conversions": 410,
                "click_through_conversions": 120,
            },
            {
                "week_start": "2025-01-13",
                "campaign_name": "UK Display Retargeting",
                "publisher_or_platform": "Programmatic DSP",
                "spend_gbp": 14200,
                "impressions": 1510000,
                "clicks": 8400,
                "view_through_conversions": 390,
                "click_through_conversions": 105,
            },
        ),
    ),
    ConnectorSpec(
        key="affiliates",
        label="Affiliate network weekly export",
        description="Weekly affiliate export for commissionable orders, revenue, and network fees.",
        columns=(
            ConnectorColumn("week_start", "Monday date for the reporting week.", non_negative=False, date_like=True),
            ConnectorColumn(
                "affiliate_partner",
                "Affiliate partner, publisher, or network segment.",
                non_negative=False,
            ),
            ConnectorColumn("orders", "Weekly attributed affiliate orders."),
            ConnectorColumn("revenue_gbp", "Weekly attributed affiliate revenue in GBP."),
            ConnectorColumn("commission_gbp", "Weekly affiliate commission in GBP."),
            ConnectorColumn("network_fee_gbp", "Weekly network or platform fee in GBP."),
        ),
        sample_rows=(
            {
                "week_start": "2025-01-06",
                "affiliate_partner": "Voucher partners",
                "orders": 860,
                "revenue_gbp": 73500,
                "commission_gbp": 5150,
                "network_fee_gbp": 620,
            },
            {
                "week_start": "2025-01-13",
                "affiliate_partner": "Content partners",
                "orders": 620,
                "revenue_gbp": 54200,
                "commission_gbp": 3500,
                "network_fee_gbp": 480,
            },
        ),
    ),
    ConnectorSpec(
        key="influencer",
        label="Influencer weekly export",
        description="Weekly creator or influencer export for paid fees, usage rights, reach, and tracked sales.",
        columns=(
            ConnectorColumn("week_start", "Monday date for the reporting week.", non_negative=False, date_like=True),
            ConnectorColumn("creator_or_campaign", "Creator name, campaign, or creator cohort.", non_negative=False),
            ConnectorColumn("fee_gbp", "Weekly creator fee or amortized fee in GBP."),
            ConnectorColumn("usage_rights_gbp", "Weekly usage-rights or content licensing cost in GBP."),
            ConnectorColumn("paid_boost_gbp", "Weekly paid boosting spend in GBP."),
            ConnectorColumn("impressions", "Weekly creator or boosted impressions."),
            ConnectorColumn("engagements", "Weekly creator or boosted engagements."),
            ConnectorColumn("tracked_orders", "Weekly tracked creator orders."),
            ConnectorColumn("tracked_revenue_gbp", "Weekly tracked creator revenue in GBP."),
        ),
        sample_rows=(
            {
                "week_start": "2025-01-06",
                "creator_or_campaign": "January creator capsule",
                "fee_gbp": 9000,
                "usage_rights_gbp": 1500,
                "paid_boost_gbp": 4500,
                "impressions": 680000,
                "engagements": 42000,
                "tracked_orders": 330,
                "tracked_revenue_gbp": 28200,
            },
            {
                "week_start": "2025-01-13",
                "creator_or_campaign": "Winter styling creators",
                "fee_gbp": 7600,
                "usage_rights_gbp": 1200,
                "paid_boost_gbp": 3800,
                "impressions": 590000,
                "engagements": 36000,
                "tracked_orders": 290,
                "tracked_revenue_gbp": 24700,
            },
        ),
    ),
    ConnectorSpec(
        key="external_controls",
        label="External controls weekly export",
        description="Weekly macro or market controls used to separate media effects from external conditions.",
        columns=(
            ConnectorColumn("week_start", "Monday date for the reporting week.", non_negative=False, date_like=True),
            ConnectorColumn(
                "consumer_confidence_index",
                "Weekly consumer confidence index or normalized market sentiment control.",
                non_negative=False,
            ),
            ConnectorColumn("inflation_rate_pct", "Weekly or monthly inflation rate aligned to reporting week."),
        ),
        sample_rows=(
            {
                "week_start": "2025-01-06",
                "consumer_confidence_index": -18.0,
                "inflation_rate_pct": 3.9,
            },
            {
                "week_start": "2025-01-13",
                "consumer_confidence_index": -17.5,
                "inflation_rate_pct": 3.8,
            },
        ),
    ),
)

CONNECTOR_LOOKUP = {spec.key: spec for spec in CONNECTOR_SPECS}


def connector_catalog() -> pd.DataFrame:
    """Return connector metadata for display."""

    return pd.DataFrame(
        [
            {
                "key": spec.key,
                "connector": spec.label,
                "description": spec.description,
                "required_columns": len(spec.columns),
            }
            for spec in CONNECTOR_SPECS
        ]
    )


def connector_template_dataframe(connector_key: str) -> pd.DataFrame:
    """Return a populated template for one connector."""

    spec = _connector_spec(connector_key)
    return pd.DataFrame(list(spec.sample_rows), columns=[column.name for column in spec.columns])


def connector_template_csv(connector_key: str) -> str:
    """Return a downloadable CSV template for one connector."""

    return connector_template_dataframe(connector_key).to_csv(index=False)


def connector_schema_dataframe(connector_key: str) -> pd.DataFrame:
    """Return connector schema details."""

    spec = _connector_spec(connector_key)
    return pd.DataFrame(
        [
            {
                "column": column.name,
                "description": column.description,
                "required": column.required,
                "non_negative": column.non_negative,
                "date_like": column.date_like,
            }
            for column in spec.columns
        ]
    )


def validate_connector_csv_text(
    connector_key: str,
    csv_text: str,
) -> tuple[pd.DataFrame | None, list[str]]:
    """Validate CSV text for a connector template."""

    spec = _connector_spec(connector_key)
    try:
        df = pd.read_csv(StringIO(csv_text))
    except Exception as exc:  # pragma: no cover - parser wording varies.
        return None, [f"CSV could not be parsed: {exc}"]

    errors = validate_connector_frame(connector_key, df)
    if errors:
        return None, errors
    return _coerce_connector_types(spec, df), []


def validate_connector_frame(connector_key: str, df: pd.DataFrame) -> list[str]:
    """Return validation errors for a connector export."""

    spec = _connector_spec(connector_key)
    errors: list[str] = []
    required = [column.name for column in spec.columns if column.required]
    missing = [column for column in required if column not in df.columns]
    if missing:
        errors.append(f"Missing required columns: {', '.join(missing)}")
        return errors

    for column in spec.columns:
        values = df[column.name]
        if values.isna().any():
            errors.append(f"{column.name} contains null values.")
        if column.date_like:
            # Parse strictly as ISO (YYYY-MM-DD) per the data contract so an
            # ambiguous locale format is rejected rather than silently misread.
            parsed = pd.to_datetime(values, format="%Y-%m-%d", errors="coerce")
            if parsed.isna().any():
                errors.append(f"{column.name} contains invalid dates.")
            elif not parsed.dt.dayofweek.eq(0).all():
                errors.append(f"{column.name} must contain Monday week-start dates.")
            continue
        if column.non_negative:
            numeric_values = pd.to_numeric(values, errors="coerce")
            if numeric_values.isna().any():
                errors.append(f"{column.name} contains non-numeric values.")
            elif (numeric_values < 0).any():
                errors.append(f"{column.name} contains negative values.")

    return errors


def _coerce_connector_types(spec: ConnectorSpec, df: pd.DataFrame) -> pd.DataFrame:
    typed = df.copy()
    for column in spec.columns:
        if column.date_like:
            typed[column.name] = pd.to_datetime(typed[column.name]).dt.strftime("%Y-%m-%d")
        elif column.non_negative:
            typed[column.name] = pd.to_numeric(typed[column.name])
    return typed


def _connector_spec(connector_key: str) -> ConnectorSpec:
    try:
        return CONNECTOR_LOOKUP[connector_key]
    except KeyError as exc:
        known = ", ".join(sorted(CONNECTOR_LOOKUP))
        raise ValueError(f"Unknown connector '{connector_key}'. Known connectors: {known}.") from exc
