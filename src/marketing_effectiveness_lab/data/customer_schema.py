"""Schema checks for customer, order, and CRM demo datasets."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class CustomerColumnSpec:
    name: str
    description: str
    data_type: str = "string"
    non_negative: bool = True
    required: bool = True
    allow_null: bool = False
    allowed_values: tuple[object, ...] | None = None


CUSTOMER_CHANNELS = (
    "paid_search",
    "paid_social",
    "organic_search",
    "email",
    "affiliates",
    "influencer",
    "display",
)

LIFECYCLE_SEGMENTS = ("New", "Active", "Lapsing", "Dormant")
VALUE_SEGMENTS = ("Low value", "Mid value", "High value", "VIP")
PRODUCT_CATEGORIES = ("Dresses", "Denim", "Knitwear", "Outerwear", "Shoes", "Accessories")
CRM_CHANNELS = ("email", "sms", "push")
CRM_CAMPAIGN_TYPES = ("welcome", "abandoned_basket", "promotion", "winback", "vip")
CRM_TREATMENT_GROUPS = ("target", "holdout")


CUSTOMER_TABLES: dict[str, tuple[CustomerColumnSpec, ...]] = {
    "customers": (
        CustomerColumnSpec("customer_id", "Stable anonymized customer identifier."),
        CustomerColumnSpec("acquisition_date", "Date the customer first entered the business.", data_type="date"),
        CustomerColumnSpec("first_order_date", "Date of the first completed order.", data_type="date"),
        CustomerColumnSpec(
            "acquisition_channel",
            "First-touch acquisition channel used for customer quality analysis.",
            allowed_values=CUSTOMER_CHANNELS,
        ),
        CustomerColumnSpec("country", "Customer market code."),
        CustomerColumnSpec("email_opt_in", "Whether the customer can receive email CRM.", data_type="flag"),
        CustomerColumnSpec("sms_opt_in", "Whether the customer can receive SMS CRM.", data_type="flag"),
        CustomerColumnSpec(
            "lifecycle_status",
            "Current lifecycle status as of the demo snapshot.",
            allowed_values=LIFECYCLE_SEGMENTS,
        ),
    ),
    "orders": (
        CustomerColumnSpec("order_id", "Stable anonymized order identifier."),
        CustomerColumnSpec("customer_id", "Customer identifier linked to customers.customer_id."),
        CustomerColumnSpec("order_date", "Completed order date.", data_type="date"),
        CustomerColumnSpec("gross_revenue_gbp", "Order revenue before refunds in GBP.", data_type="numeric"),
        CustomerColumnSpec("discount_gbp", "Discount value applied to the order in GBP.", data_type="numeric"),
        CustomerColumnSpec("refund_gbp", "Refunded value in GBP.", data_type="numeric"),
        CustomerColumnSpec("shipping_revenue_gbp", "Shipping revenue collected in GBP.", data_type="numeric"),
        CustomerColumnSpec(
            "gross_margin_gbp",
            "Estimated gross margin after discounts and refunds.",
            data_type="numeric",
        ),
        CustomerColumnSpec(
            "order_status",
            "Commercial order status.",
            allowed_values=("completed", "partially_refunded", "refunded"),
        ),
    ),
    "order_items": (
        CustomerColumnSpec("order_item_id", "Stable anonymized order-item identifier."),
        CustomerColumnSpec("order_id", "Order identifier linked to orders.order_id."),
        CustomerColumnSpec("product_category", "Fashion product category.", allowed_values=PRODUCT_CATEGORIES),
        CustomerColumnSpec("quantity", "Units sold for the line item.", data_type="numeric"),
        CustomerColumnSpec("item_revenue_gbp", "Line-item revenue in GBP.", data_type="numeric"),
        CustomerColumnSpec("item_margin_gbp", "Line-item gross margin in GBP.", data_type="numeric"),
    ),
    "returns": (
        CustomerColumnSpec("return_id", "Stable anonymized return identifier."),
        CustomerColumnSpec("order_id", "Returned order identifier linked to orders.order_id."),
        CustomerColumnSpec("customer_id", "Customer identifier linked to customers.customer_id."),
        CustomerColumnSpec("return_date", "Date the return was processed.", data_type="date"),
        CustomerColumnSpec("refund_gbp", "Refunded value in GBP.", data_type="numeric"),
        CustomerColumnSpec(
            "return_reason",
            "Reason code for return diagnostics.",
            allowed_values=("fit", "quality", "changed_mind", "late_delivery", "other"),
        ),
    ),
    "crm_campaigns": (
        CustomerColumnSpec("campaign_id", "Stable anonymized CRM campaign identifier."),
        CustomerColumnSpec("campaign_name", "Business-facing campaign name."),
        CustomerColumnSpec("campaign_type", "CRM lifecycle campaign type.", allowed_values=CRM_CAMPAIGN_TYPES),
        CustomerColumnSpec("channel", "CRM contact channel.", allowed_values=CRM_CHANNELS),
        CustomerColumnSpec("start_date", "Campaign start date.", data_type="date"),
        CustomerColumnSpec("end_date", "Campaign end date.", data_type="date"),
        CustomerColumnSpec("target_segment", "Lifecycle or value segment targeted by the campaign."),
        CustomerColumnSpec("campaign_cost_gbp", "Fixed campaign operating cost in GBP.", data_type="numeric"),
        CustomerColumnSpec(
            "incentive_cost_per_customer_gbp",
            "Expected incentive or discount cost per contacted customer.",
            data_type="numeric",
        ),
    ),
    "crm_events": (
        CustomerColumnSpec("event_id", "Stable anonymized CRM event identifier."),
        CustomerColumnSpec("campaign_id", "Campaign identifier linked to crm_campaigns.campaign_id."),
        CustomerColumnSpec("customer_id", "Customer identifier linked to customers.customer_id."),
        CustomerColumnSpec("event_date", "Date of CRM exposure or holdout assignment.", data_type="date"),
        CustomerColumnSpec("treatment_group", "Experiment group assignment.", allowed_values=CRM_TREATMENT_GROUPS),
        CustomerColumnSpec("sent_flag", "Whether a message was sent.", data_type="flag"),
        CustomerColumnSpec("opened_flag", "Whether the message was opened.", data_type="flag"),
        CustomerColumnSpec("clicked_flag", "Whether the message was clicked.", data_type="flag"),
        CustomerColumnSpec(
            "converted_flag",
            "Whether the customer converted in the campaign window.",
            data_type="flag",
        ),
        CustomerColumnSpec(
            "attributed_order_id",
            "Optional order identifier for campaign-window conversion.",
            allow_null=True,
        ),
        CustomerColumnSpec("revenue_gbp", "Campaign-window revenue in GBP.", data_type="numeric"),
        CustomerColumnSpec("gross_margin_gbp", "Campaign-window gross margin in GBP.", data_type="numeric"),
        CustomerColumnSpec("unsubscribe_flag", "Whether the customer unsubscribed after contact.", data_type="flag"),
    ),
    "customer_segments": (
        CustomerColumnSpec("customer_id", "Customer identifier linked to customers.customer_id."),
        CustomerColumnSpec("snapshot_date", "Date the segment snapshot was calculated.", data_type="date"),
        CustomerColumnSpec("recency_days", "Days since latest completed order.", data_type="numeric"),
        CustomerColumnSpec("order_count", "Completed order count.", data_type="numeric"),
        CustomerColumnSpec("revenue_gbp", "Historical gross revenue in GBP.", data_type="numeric"),
        CustomerColumnSpec("gross_margin_gbp", "Historical gross margin in GBP.", data_type="numeric"),
        CustomerColumnSpec("discount_rate", "Discount as a share of gross revenue.", data_type="numeric"),
        CustomerColumnSpec("return_rate", "Refunds as a share of gross revenue.", data_type="numeric"),
        CustomerColumnSpec("lifecycle_segment", "Lifecycle segment.", allowed_values=LIFECYCLE_SEGMENTS),
        CustomerColumnSpec("value_segment", "Margin-value segment.", allowed_values=VALUE_SEGMENTS),
        CustomerColumnSpec(
            "contactable_flag",
            "Whether the customer can receive at least one CRM channel.",
            data_type="flag",
        ),
    ),
}

UNIQUE_KEYS = {
    "customers": "customer_id",
    "orders": "order_id",
    "order_items": "order_item_id",
    "returns": "return_id",
    "crm_campaigns": "campaign_id",
    "crm_events": "event_id",
    "customer_segments": "customer_id",
}


def validate_customer_table(table_name: str, df: pd.DataFrame) -> list[str]:
    """Return validation errors for one customer/CRM table."""

    if table_name not in CUSTOMER_TABLES:
        return [f"Unknown customer table: {table_name}"]

    errors: list[str] = []
    specs = CUSTOMER_TABLES[table_name]
    required_names = [spec.name for spec in specs if spec.required]
    missing = [name for name in required_names if name not in df.columns]
    if missing:
        errors.append(f"{table_name}: missing required columns: {', '.join(missing)}")
        return errors

    unique_key = UNIQUE_KEYS[table_name]
    if df[unique_key].duplicated().any():
        errors.append(f"{table_name}: {unique_key} must be unique.")

    for spec in specs:
        series = df[spec.name]
        if not spec.allow_null and series.isna().any():
            errors.append(f"{table_name}: {spec.name} contains null values.")

        present_values = series.dropna()
        if spec.data_type == "date":
            parsed_dates = pd.to_datetime(present_values, errors="coerce")
            if parsed_dates.isna().any():
                errors.append(f"{table_name}: {spec.name} contains invalid dates.")
        elif spec.data_type == "flag":
            bad_values = set(present_values.unique()).difference({0, 1})
            if bad_values:
                errors.append(f"{table_name}: {spec.name} must contain only 0/1 values.")
        elif spec.data_type == "numeric":
            numeric_values = pd.to_numeric(present_values, errors="coerce")
            if numeric_values.isna().any():
                errors.append(f"{table_name}: {spec.name} contains non-numeric values.")
            if spec.non_negative and (numeric_values < 0).any():
                errors.append(f"{table_name}: {spec.name} contains negative values.")

        if spec.allowed_values is not None:
            bad_values = set(present_values.unique()).difference(spec.allowed_values)
            if bad_values:
                errors.append(f"{table_name}: {spec.name} contains unsupported values: {sorted(bad_values)}")

    return errors


def validate_customer_dataset(tables: Mapping[str, pd.DataFrame]) -> list[str]:
    """Return validation errors for the full customer/CRM dataset."""

    errors: list[str] = []
    missing_tables = [table_name for table_name in CUSTOMER_TABLES if table_name not in tables]
    if missing_tables:
        errors.append(f"Missing customer tables: {', '.join(missing_tables)}")
        return errors

    for table_name, df in tables.items():
        errors.extend(validate_customer_table(table_name, df))

    if errors:
        return errors

    customers = tables["customers"]
    orders = tables["orders"]
    order_items = tables["order_items"]
    returns = tables["returns"]
    crm_campaigns = tables["crm_campaigns"]
    crm_events = tables["crm_events"]
    customer_segments = tables["customer_segments"]

    errors.extend(
        _foreign_key_errors(
            orders["customer_id"],
            customers["customer_id"],
            child_table="orders",
            child_key="customer_id",
            parent_table="customers",
        )
    )
    errors.extend(
        _foreign_key_errors(
            order_items["order_id"],
            orders["order_id"],
            child_table="order_items",
            child_key="order_id",
            parent_table="orders",
        )
    )
    errors.extend(
        _foreign_key_errors(
            returns["order_id"],
            orders["order_id"],
            child_table="returns",
            child_key="order_id",
            parent_table="orders",
        )
    )
    errors.extend(
        _foreign_key_errors(
            returns["customer_id"],
            customers["customer_id"],
            child_table="returns",
            child_key="customer_id",
            parent_table="customers",
        )
    )
    errors.extend(
        _foreign_key_errors(
            crm_events["campaign_id"],
            crm_campaigns["campaign_id"],
            child_table="crm_events",
            child_key="campaign_id",
            parent_table="crm_campaigns",
        )
    )
    errors.extend(
        _foreign_key_errors(
            crm_events["customer_id"],
            customers["customer_id"],
            child_table="crm_events",
            child_key="customer_id",
            parent_table="customers",
        )
    )
    errors.extend(
        _foreign_key_errors(
            customer_segments["customer_id"],
            customers["customer_id"],
            child_table="customer_segments",
            child_key="customer_id",
            parent_table="customers",
        )
    )

    attributed_order_ids = crm_events["attributed_order_id"].dropna()
    if not attributed_order_ids.empty:
        errors.extend(
            _foreign_key_errors(
                attributed_order_ids,
                orders["order_id"],
                child_table="crm_events",
                child_key="attributed_order_id",
                parent_table="orders",
            )
        )

    if len(customer_segments) != len(customers):
        errors.append("customer_segments: expected one segment row per customer.")

    return errors


def customer_schema_as_records(
    tables: Mapping[str, Iterable[CustomerColumnSpec]] = CUSTOMER_TABLES,
) -> list[dict[str, object]]:
    """Represent customer schemas as serializable records."""

    return [
        {
            "table": table_name,
            "name": column.name,
            "description": column.description,
            "data_type": column.data_type,
            "non_negative": column.non_negative,
            "required": column.required,
            "allow_null": column.allow_null,
            "allowed_values": list(column.allowed_values) if column.allowed_values else None,
        }
        for table_name, columns in tables.items()
        for column in columns
    ]


def _foreign_key_errors(
    child_values: pd.Series,
    parent_values: pd.Series,
    *,
    child_table: str,
    child_key: str,
    parent_table: str,
) -> list[str]:
    missing_values = set(child_values.dropna()).difference(set(parent_values.dropna()))
    if missing_values:
        return [
            f"{child_table}: {child_key} contains {len(missing_values):,} value(s) not found in {parent_table}."
        ]
    return []
