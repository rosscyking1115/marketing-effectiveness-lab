# Data Dictionary

## Dataset

`data/demo/fashion_retail_weekly.csv`

Weekly UK fashion ecommerce marketing effectiveness dataset.

## Fields

| Column | Description |
| --- | --- |
| `week_start` | Monday date for the reporting week. |
| `revenue_gbp` | Weekly ecommerce revenue in GBP. |
| `orders` | Weekly ecommerce orders. |
| `new_customers` | Weekly first-time customers. |
| `average_order_value_gbp` | Weekly average order value in GBP. |
| `paid_search_spend_gbp` | Weekly paid search media spend in GBP. |
| `paid_social_spend_gbp` | Weekly paid social media spend in GBP. |
| `display_spend_gbp` | Weekly display media spend in GBP. |
| `affiliates_spend_gbp` | Weekly affiliate channel spend in GBP. |
| `email_spend_gbp` | Weekly email/CRM campaign spend in GBP. |
| `influencer_spend_gbp` | Weekly influencer marketing spend in GBP. |
| `organic_search_sessions` | Weekly organic search sessions. |
| `promotion_depth_pct` | Average weekly promotional discount depth. |
| `promotion_flag` | Whether a major promotion ran that week. |
| `holiday_flag` | Whether the week contains a major UK retail holiday period. |
| `season_spring_summer` | Spring/summer seasonal collection flag. |
| `season_autumn_winter` | Autumn/winter seasonal collection flag. |
| `consumer_confidence_index` | Synthetic UK consumer confidence control. |
| `inflation_rate_pct` | Synthetic UK inflation control. |

## Notes

The demo dataset is generated for development and portfolio use. It is not ASOS data and does not copy any private brand data.

The schema is intentionally close to what a real business could provide through weekly spreadsheet exports or warehouse tables.

The dashboard can also accept uploaded CSV files that follow this schema. Uploaded files are parsed in memory in the current prototype.

## Connector Templates

The app also provides validation templates for common upstream exports:

- GA4 traffic and conversion export
- Google Ads weekly export
- Meta Ads weekly export
- Shopify or ecommerce orders export
- CRM and lifecycle export

These templates do not call external APIs. They define safe CSV contracts for exports that can be assembled into the weekly MMM dataset.

## Weekly Assembly Mapping

The connector assembly pipeline treats Shopify/ecommerce as the reconciled outcome source and maps optional marketing exports onto that weekly spine:

| Connector | Weekly MMM fields |
| --- | --- |
| Shopify/ecommerce | `revenue_gbp`, `orders`, `new_customers`, `average_order_value_gbp`, `promotion_depth_pct`, `promotion_flag`, seasonal and holiday defaults |
| Google Ads | `paid_search_spend_gbp` |
| Meta Ads | `paid_social_spend_gbp` |
| CRM and lifecycle | `email_spend_gbp` |
| GA4 | `organic_search_sessions` from organic source/medium rows |

Display, affiliates, and influencer spend default to `0` until those connector contracts are added. Consumer confidence and inflation default to neutral `0` placeholders unless supplied in a future controls connector.

## Assembly Diagnostics

The connector assembly workflow now reports pre-modeling diagnostics:

- Weekly schema validation status.
- Weekly history sufficiency for the current holdout workflow.
- Outcome quality for revenue and orders.
- Customer-count anomalies.
- Active media channel coverage.
- Organic search coverage.
- Explicit zero-default channel notes.
- Source coverage by connector.

## Validation Rules

- `week_start` must be a Monday date.
- Weekly dates must be unique and continuous.
- Required columns must be present.
- Numeric columns must contain numeric values.
- Non-negative columns cannot contain negative values.
- Flag columns must contain only `0` and `1`.
