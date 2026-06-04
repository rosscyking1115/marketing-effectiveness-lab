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

The dataset is generated for development and portfolio use. It is not ASOS data and does not copy any private brand data.

The schema is intentionally close to what a real business could provide through weekly spreadsheet exports or warehouse tables.

