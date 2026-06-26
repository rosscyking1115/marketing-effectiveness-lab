"""Customer, order, and CRM demo data generation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from marketing_effectiveness_lab.data.customer_schema import (
    CUSTOMER_CHANNELS,
    LIFECYCLE_SEGMENTS,
    PRODUCT_CATEGORIES,
    customer_schema_as_records,
    validate_customer_dataset,
)


@dataclass(frozen=True)
class CustomerDemoDataset:
    customers: pd.DataFrame
    orders: pd.DataFrame
    order_items: pd.DataFrame
    returns: pd.DataFrame
    crm_campaigns: pd.DataFrame
    crm_events: pd.DataFrame
    customer_segments: pd.DataFrame
    metadata: dict[str, object]

    def as_tables(self) -> dict[str, pd.DataFrame]:
        """Return customer demo tables keyed by output name."""

        return {
            "customers": self.customers,
            "orders": self.orders,
            "order_items": self.order_items,
            "returns": self.returns,
            "crm_campaigns": self.crm_campaigns,
            "crm_events": self.crm_events,
            "customer_segments": self.customer_segments,
        }


CHANNEL_PROFILES = {
    "paid_search": {"weight": 0.20, "aov": 70, "repeat": 0.52, "margin": 0.50, "discount": 0.10},
    "paid_social": {"weight": 0.26, "aov": 62, "repeat": 0.44, "margin": 0.46, "discount": 0.16},
    "organic_search": {"weight": 0.18, "aov": 68, "repeat": 0.56, "margin": 0.53, "discount": 0.08},
    "email": {"weight": 0.10, "aov": 75, "repeat": 0.64, "margin": 0.55, "discount": 0.09},
    "affiliates": {"weight": 0.11, "aov": 59, "repeat": 0.41, "margin": 0.43, "discount": 0.18},
    "influencer": {"weight": 0.09, "aov": 72, "repeat": 0.47, "margin": 0.48, "discount": 0.13},
    "display": {"weight": 0.06, "aov": 57, "repeat": 0.36, "margin": 0.42, "discount": 0.19},
}


def generate_customer_demo_data(seed: int = 42, customer_count: int = 2_400) -> CustomerDemoDataset:
    """Generate an anonymized ecommerce customer and CRM dataset."""

    rng = np.random.default_rng(seed)
    start_date = pd.Timestamp("2023-01-02")
    end_date = pd.Timestamp("2025-12-31")
    snapshot_date = end_date

    customers = _generate_customers(rng, customer_count, start_date, end_date)
    orders, returns = _generate_orders_and_returns(rng, customers, end_date)
    order_items = _generate_order_items(rng, orders)
    customer_segments = _build_customer_segments(customers, orders, snapshot_date)
    customers = customers.drop(columns=["lifecycle_status"]).merge(
        customer_segments[["customer_id", "lifecycle_segment"]].rename(
            columns={"lifecycle_segment": "lifecycle_status"}
        ),
        on="customer_id",
        how="left",
    )
    crm_campaigns = _generate_crm_campaigns()
    crm_events = _generate_crm_events(rng, customers, orders, customer_segments, crm_campaigns)

    metadata = {
        "scenario": "UK fashion ecommerce customer and CRM demo dataset",
        "seed": seed,
        "currency": "GBP",
        "grain": "customer/order/campaign",
        "customer_count": customer_count,
        "date_window": {
            "start_date": str(start_date.date()),
            "end_date": str(end_date.date()),
            "snapshot_date": str(snapshot_date.date()),
        },
        "notes": [
            "Customer, order, and CRM records are synthetic and anonymized for portfolio use.",
            "The dataset is designed to support RFM, cohort, CRM incrementality, and customer-profit workflows.",
            "CRM event conversion fields are generated from treatment/holdout assignment "
            "and should not be read as attribution.",
        ],
        "schema": customer_schema_as_records(),
    }

    return CustomerDemoDataset(
        customers=customers,
        orders=orders,
        order_items=order_items,
        returns=returns,
        crm_campaigns=crm_campaigns,
        crm_events=crm_events,
        customer_segments=customer_segments,
        metadata=metadata,
    )


def write_customer_outputs(dataset: CustomerDemoDataset, output_dir: Path) -> None:
    """Write generated customer demo tables and metadata."""

    output_dir.mkdir(parents=True, exist_ok=True)
    for table_name, table in dataset.as_tables().items():
        table.to_csv(output_dir / f"{table_name}.csv", index=False)

    with (output_dir / "customer_ground_truth_metadata.json").open("w", encoding="utf-8") as fp:
        json.dump(dataset.metadata, fp, indent=2)


def generate_customer_data_and_validate(
    output_dir: Path,
    *,
    seed: int = 42,
    customer_count: int = 2_400,
) -> CustomerDemoDataset:
    """Generate, validate, and write the customer demo dataset."""

    dataset = generate_customer_demo_data(seed=seed, customer_count=customer_count)
    errors = validate_customer_dataset(dataset.as_tables())
    if errors:
        raise ValueError("Customer dataset validation failed:\n- " + "\n- ".join(errors))
    write_customer_outputs(dataset, output_dir)
    return dataset


def _generate_customers(
    rng: np.random.Generator,
    customer_count: int,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
) -> pd.DataFrame:
    channel_weights = np.array([CHANNEL_PROFILES[channel]["weight"] for channel in CUSTOMER_CHANNELS])
    channel_weights = channel_weights / channel_weights.sum()
    acquisition_channels = rng.choice(CUSTOMER_CHANNELS, size=customer_count, p=channel_weights)
    acquisition_offsets = rng.integers(0, (end_date - start_date).days - 60, size=customer_count)
    acquisition_dates = start_date + pd.to_timedelta(acquisition_offsets, unit="D")
    first_order_lag = rng.integers(0, 15, size=customer_count)
    first_order_dates = acquisition_dates + pd.to_timedelta(first_order_lag, unit="D")
    email_opt_in = rng.binomial(1, 0.74, size=customer_count)
    sms_opt_in = rng.binomial(1, 0.28, size=customer_count)

    return pd.DataFrame(
        {
            "customer_id": [f"CUST-{idx:06d}" for idx in range(1, customer_count + 1)],
            "acquisition_date": acquisition_dates.strftime("%Y-%m-%d"),
            "first_order_date": first_order_dates.strftime("%Y-%m-%d"),
            "acquisition_channel": acquisition_channels,
            "country": "GB",
            "email_opt_in": email_opt_in,
            "sms_opt_in": sms_opt_in,
            "lifecycle_status": "New",
        }
    )


def _generate_orders_and_returns(
    rng: np.random.Generator,
    customers: pd.DataFrame,
    end_date: pd.Timestamp,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    orders: list[dict[str, object]] = []
    returns: list[dict[str, object]] = []
    order_idx = 1
    return_idx = 1

    for customer in customers.to_dict("records"):
        channel = str(customer["acquisition_channel"])
        profile = CHANNEL_PROFILES[channel]
        order_dates = _customer_order_dates(
            rng,
            pd.Timestamp(customer["first_order_date"]),
            end_date,
            repeat_probability=float(profile["repeat"]),
        )
        for order_date in order_dates:
            order_id = f"ORD-{order_idx:07d}"
            gross_revenue = float(max(18, rng.lognormal(np.log(profile["aov"]), 0.32)))
            discount_rate = float(np.clip(rng.normal(profile["discount"], 0.04), 0, 0.38))
            discount = gross_revenue * discount_rate
            return_probability = float(np.clip(0.11 + discount_rate * 0.22, 0.05, 0.26))
            refunded = rng.random() < return_probability
            refund_rate = float(rng.uniform(0.25, 1.0)) if refunded else 0.0
            refund = gross_revenue * refund_rate
            shipping_revenue = float(rng.choice([0, 3.95, 4.95], p=[0.55, 0.30, 0.15]))
            margin_rate = float(np.clip(rng.normal(profile["margin"], 0.06), 0.28, 0.68))
            gross_margin = max((gross_revenue - discount - refund) * margin_rate, 0)
            status = "completed"
            if refund_rate >= 0.95:
                status = "refunded"
            elif refund_rate > 0:
                status = "partially_refunded"

            orders.append(
                {
                    "order_id": order_id,
                    "customer_id": customer["customer_id"],
                    "order_date": order_date.strftime("%Y-%m-%d"),
                    "gross_revenue_gbp": round(gross_revenue, 2),
                    "discount_gbp": round(discount, 2),
                    "refund_gbp": round(refund, 2),
                    "shipping_revenue_gbp": shipping_revenue,
                    "gross_margin_gbp": round(gross_margin, 2),
                    "order_status": status,
                }
            )

            if refunded:
                returns.append(
                    {
                        "return_id": f"RET-{return_idx:06d}",
                        "order_id": order_id,
                        "customer_id": customer["customer_id"],
                        "return_date": (order_date + pd.Timedelta(days=int(rng.integers(4, 29)))).strftime(
                            "%Y-%m-%d"
                        ),
                        "refund_gbp": round(refund, 2),
                        "return_reason": str(
                            rng.choice(["fit", "quality", "changed_mind", "late_delivery", "other"])
                        ),
                    }
                )
                return_idx += 1

            order_idx += 1

    return pd.DataFrame(orders), pd.DataFrame(returns)


def _customer_order_dates(
    rng: np.random.Generator,
    first_order_date: pd.Timestamp,
    end_date: pd.Timestamp,
    *,
    repeat_probability: float,
) -> list[pd.Timestamp]:
    order_dates = [first_order_date]
    current_date = first_order_date
    while rng.random() < repeat_probability and current_date < end_date - pd.Timedelta(days=20):
        current_date = current_date + pd.Timedelta(days=int(rng.gamma(shape=2.4, scale=32)))
        if current_date <= end_date:
            order_dates.append(current_date)
        repeat_probability *= 0.82
    return order_dates


def _generate_order_items(rng: np.random.Generator, orders: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    item_idx = 1
    category_weights = np.array([0.22, 0.18, 0.17, 0.12, 0.16, 0.15])

    for order in orders.to_dict("records"):
        item_count = int(rng.choice([1, 2, 3], p=[0.62, 0.29, 0.09]))
        shares = rng.dirichlet(np.ones(item_count))
        categories = rng.choice(PRODUCT_CATEGORIES, size=item_count, replace=True, p=category_weights)
        for share, category in zip(shares, categories, strict=True):
            rows.append(
                {
                    "order_item_id": f"ITEM-{item_idx:08d}",
                    "order_id": order["order_id"],
                    "product_category": str(category),
                    "quantity": int(rng.choice([1, 2], p=[0.86, 0.14])),
                    "item_revenue_gbp": round(float(order["gross_revenue_gbp"]) * float(share), 2),
                    "item_margin_gbp": round(float(order["gross_margin_gbp"]) * float(share), 2),
                }
            )
            item_idx += 1

    return pd.DataFrame(rows)


def _build_customer_segments(
    customers: pd.DataFrame,
    orders: pd.DataFrame,
    snapshot_date: pd.Timestamp,
) -> pd.DataFrame:
    order_summary = orders.groupby("customer_id", as_index=False).agg(
        latest_order_date=("order_date", "max"),
        order_count=("order_id", "count"),
        revenue_gbp=("gross_revenue_gbp", "sum"),
        discount_gbp=("discount_gbp", "sum"),
        refund_gbp=("refund_gbp", "sum"),
        gross_margin_gbp=("gross_margin_gbp", "sum"),
    )
    merged = customers.merge(order_summary, on="customer_id", how="left")
    latest_order = pd.to_datetime(merged["latest_order_date"])
    recency_days = (snapshot_date - latest_order).dt.days.clip(lower=0)
    discount_rate = (merged["discount_gbp"] / merged["revenue_gbp"]).fillna(0).clip(0, 1)
    return_rate = (merged["refund_gbp"] / merged["revenue_gbp"]).fillna(0).clip(0, 1)

    lifecycle_segment = pd.cut(
        recency_days,
        bins=[-1, 30, 120, 240, 10_000],
        labels=LIFECYCLE_SEGMENTS,
    ).astype(str)
    value_segment = pd.qcut(
        merged["gross_margin_gbp"].rank(method="first"),
        q=4,
        labels=["Low value", "Mid value", "High value", "VIP"],
    ).astype(str)
    contactable = ((merged["email_opt_in"] == 1) | (merged["sms_opt_in"] == 1)).astype(int)

    return pd.DataFrame(
        {
            "customer_id": merged["customer_id"],
            "snapshot_date": snapshot_date.strftime("%Y-%m-%d"),
            "recency_days": recency_days.astype(int),
            "order_count": merged["order_count"].astype(int),
            "revenue_gbp": merged["revenue_gbp"].round(2),
            "gross_margin_gbp": merged["gross_margin_gbp"].round(2),
            "discount_rate": discount_rate.round(4),
            "return_rate": return_rate.round(4),
            "lifecycle_segment": lifecycle_segment,
            "value_segment": value_segment,
            "contactable_flag": contactable,
        }
    )


def _generate_crm_campaigns() -> pd.DataFrame:
    rows = [
        (
            "CRM-2024-01",
            "January welcome series",
            "welcome",
            "email",
            "2024-01-08",
            "2024-01-21",
            "New",
            1250,
            0,
        ),
        (
            "CRM-2024-03",
            "Spring basket recovery",
            "abandoned_basket",
            "email",
            "2024-03-04",
            "2024-03-17",
            "Active",
            1600,
            3,
        ),
        (
            "CRM-2024-06",
            "Summer sale early access",
            "promotion",
            "email",
            "2024-06-10",
            "2024-06-23",
            "Active",
            2200,
            5,
        ),
        (
            "CRM-2024-09",
            "Autumn VIP preview",
            "vip",
            "email",
            "2024-09-02",
            "2024-09-15",
            "VIP",
            1800,
            0,
        ),
        (
            "CRM-2024-11",
            "Black Friday lapsed winback",
            "winback",
            "email",
            "2024-11-18",
            "2024-12-01",
            "Dormant",
            2600,
            7,
        ),
        (
            "CRM-2025-02",
            "New season welcome",
            "welcome",
            "email",
            "2025-02-03",
            "2025-02-16",
            "New",
            1350,
            0,
        ),
        (
            "CRM-2025-04",
            "Basket recovery SMS test",
            "abandoned_basket",
            "sms",
            "2025-04-07",
            "2025-04-20",
            "Active",
            1750,
            2,
        ),
        (
            "CRM-2025-07",
            "Summer sale winback",
            "winback",
            "email",
            "2025-07-07",
            "2025-07-20",
            "Lapsing",
            2400,
            6,
        ),
        (
            "CRM-2025-10",
            "Outerwear VIP launch",
            "vip",
            "push",
            "2025-10-06",
            "2025-10-19",
            "VIP",
            1550,
            0,
        ),
        (
            "CRM-2025-11",
            "Black Friday retention",
            "promotion",
            "email",
            "2025-11-17",
            "2025-11-30",
            "Active",
            2800,
            8,
        ),
    ]
    return pd.DataFrame(
        rows,
        columns=[
            "campaign_id",
            "campaign_name",
            "campaign_type",
            "channel",
            "start_date",
            "end_date",
            "target_segment",
            "campaign_cost_gbp",
            "incentive_cost_per_customer_gbp",
        ],
    )


def _generate_crm_events(
    rng: np.random.Generator,
    customers: pd.DataFrame,
    orders: pd.DataFrame,
    customer_segments: pd.DataFrame,
    campaigns: pd.DataFrame,
) -> pd.DataFrame:
    customer_lookup = customers.set_index("customer_id")
    segment_lookup = customer_segments.set_index("customer_id")
    orders_by_customer = {
        customer_id: group.sort_values("order_date").to_dict("records")
        for customer_id, group in orders.groupby("customer_id")
    }
    rows: list[dict[str, object]] = []
    event_idx = 1

    for campaign in campaigns.to_dict("records"):
        eligible = _eligible_customers_for_campaign(customers, customer_segments, campaign)
        sample_size = min(len(eligible), 620 if campaign["target_segment"] != "VIP" else 280)
        if sample_size == 0:
            continue
        selected_ids = rng.choice(eligible["customer_id"].to_numpy(), size=sample_size, replace=False)
        for customer_id in selected_ids:
            treatment_group = str(rng.choice(["target", "holdout"], p=[0.88, 0.12]))
            channel = str(campaign["channel"])
            opted_in = _is_opted_in(customer_lookup.loc[customer_id], channel)
            sent_flag = int(treatment_group == "target" and opted_in)
            opened_flag = int(sent_flag and rng.random() < _open_probability(channel))
            clicked_flag = int(opened_flag and rng.random() < 0.24)
            segment = segment_lookup.loc[customer_id]
            baseline_conversion = _baseline_crm_conversion(segment)
            treatment_lift = 0.025 if sent_flag else 0.0
            converted_flag = int(rng.random() < baseline_conversion + treatment_lift)
            attributed_order = _campaign_window_order(
                orders_by_customer.get(customer_id, []),
                pd.Timestamp(campaign["start_date"]),
                pd.Timestamp(campaign["end_date"]) + pd.Timedelta(days=14),
            )
            revenue = float(attributed_order["gross_revenue_gbp"]) if converted_flag and attributed_order else 0.0
            margin = float(attributed_order["gross_margin_gbp"]) if converted_flag and attributed_order else 0.0
            unsubscribe_probability = (
                0.004 + float(campaign["incentive_cost_per_customer_gbp"]) * 0.0005
            )
            unsubscribe_flag = int(sent_flag and rng.random() < unsubscribe_probability)
            attributed_order_id = (
                attributed_order["order_id"] if converted_flag and attributed_order else None
            )

            rows.append(
                {
                    "event_id": f"EVT-{event_idx:08d}",
                    "campaign_id": campaign["campaign_id"],
                    "customer_id": customer_id,
                    "event_date": campaign["start_date"],
                    "treatment_group": treatment_group,
                    "sent_flag": sent_flag,
                    "opened_flag": opened_flag,
                    "clicked_flag": clicked_flag,
                    "converted_flag": converted_flag,
                    "attributed_order_id": attributed_order_id,
                    "revenue_gbp": round(revenue, 2),
                    "gross_margin_gbp": round(margin, 2),
                    "unsubscribe_flag": unsubscribe_flag,
                }
            )
            event_idx += 1

    return pd.DataFrame(rows)


def _eligible_customers_for_campaign(
    customers: pd.DataFrame,
    customer_segments: pd.DataFrame,
    campaign: dict[str, object],
) -> pd.DataFrame:
    joined = customers.merge(customer_segments, on="customer_id", how="inner")
    target_segment = str(campaign["target_segment"])
    if target_segment in set(LIFECYCLE_SEGMENTS):
        joined = joined[joined["lifecycle_segment"] == target_segment]
    elif target_segment == "VIP":
        joined = joined[joined["value_segment"] == "VIP"]
    return joined[joined["contactable_flag"] == 1]


def _is_opted_in(customer: pd.Series, channel: str) -> bool:
    if channel == "sms":
        return bool(customer["sms_opt_in"])
    if channel in {"email", "push"}:
        return bool(customer["email_opt_in"])
    return False


def _open_probability(channel: str) -> float:
    if channel == "sms":
        return 0.68
    if channel == "push":
        return 0.42
    return 0.36


def _baseline_crm_conversion(segment: pd.Series) -> float:
    lifecycle_base = {
        "New": 0.050,
        "Active": 0.075,
        "Lapsing": 0.040,
        "Dormant": 0.022,
    }
    value_multiplier = {
        "Low value": 0.75,
        "Mid value": 1.00,
        "High value": 1.18,
        "VIP": 1.35,
    }
    return lifecycle_base[str(segment["lifecycle_segment"])] * value_multiplier[str(segment["value_segment"])]


def _campaign_window_order(
    customer_orders: list[dict[str, object]],
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
) -> dict[str, object] | None:
    for order in customer_orders:
        order_date = pd.Timestamp(order["order_date"])
        if start_date <= order_date <= end_date:
            return order
    return None
