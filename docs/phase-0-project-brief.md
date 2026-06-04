# Phase 0 Project Brief: Marketing Effectiveness Lab

## Working Title

Marketing Effectiveness Lab

## Positioning

This project is an end-to-end marketing measurement lab for an ASOS-style fashion ecommerce business. It estimates incremental marketing impact, explains revenue contribution by channel, and supports budget reallocation decisions under uncertainty.

The project is designed to support the broadest useful data science path: marketing, commercial, product, retail, and analytics consulting. The strongest positioning is:

> Commercial Data Scientist with a marketing measurement and causal inference specialty.

This keeps the project relevant to marketing analytics roles while also showing business impact, product thinking, econometrics, causal inference, and stakeholder communication.

## What "ASOS-Style" Means

ASOS-style does not mean copying ASOS data or branding. It means using a realistic fashion ecommerce scenario inspired by the type of business ASOS represents:

- Online-first retail
- Fashion, apparel, footwear, accessories, or beauty categories
- Frequent promotions and seasonal demand
- Multiple paid and owned marketing channels
- High dependence on digital acquisition and retention
- Commercial KPIs such as revenue, orders, new customers, average order value, and margin
- Marketing questions around paid search, paid social, influencers, affiliates, email, display, and promotions

This is a strong scenario because it is realistic, recognizable, and employable across retail, luxury, beauty, ecommerce, consumer brands, agencies, and consultancies.

## Recommended Project Shape

Version 1 should be small but polished:

1. A technical repo with clean data generation, feature engineering, econometric modeling, MMM, causal checks, and tests.
2. An analyst dashboard that lets a user inspect trends, model results, contribution, ROI, and uncertainty.
3. A later decision-tool layer for budget simulation and optimization.

The app should not be a full SaaS product at first. It should be a product-quality demo on top of a serious analytical foundation.

This hybrid is stronger than a notebook-only project because it shows:

- Data science depth
- Engineering discipline
- Business usability
- Communication of uncertainty
- Product sense
- Future SaaS potential

## Target User

Primary user:

- Marketing or commercial data scientist at a fashion ecommerce company.

Secondary users:

- Marketing analyst
- Media effectiveness analyst
- Analytics consultant
- Growth analyst
- Retail/product analyst
- Brand or performance marketing manager

## Core Business Question

For a UK fashion ecommerce brand, how should marketing budget be allocated across channels to improve revenue while accounting for seasonality, promotions, diminishing returns, and uncertainty?

## Geography and Currency

- Market: United Kingdom
- Currency: GBP
- Time grain: Weekly
- Initial time horizon: 2 to 3 years of weekly data

## Starter Marketing Channels

- Paid search
- Paid social
- Display
- Affiliates
- Email
- Influencer
- Organic search
- Promotions

Paid channels will be modeled with spend, impressions, clicks, saturation, and adstock effects where appropriate. Owned or organic channels may be included as controls or supporting drivers, depending on the model design.

## Primary Business Outcome

Version 1 should use revenue as the main outcome.

Supporting outcomes:

- Orders
- New customers
- Average order value
- Gross margin or contribution margin, if we want a more commercially advanced version later

Revenue is the best starting target because it is intuitive, widely used in MMM, and easier to explain to business stakeholders. Profit can become a later enhancement once the core model works.

## Data Strategy

The preferred long-term design is dataset-agnostic: the lab should accept real company or client marketing data through a documented schema.

For version 1, there are three possible data sources:

1. Public or demo MMM datasets from open-source libraries.
2. User-provided real exports from ad platforms, ecommerce tools, analytics tools, or spreadsheets.
3. A hybrid dataset that combines realistic marketing simulation with real public context data such as holidays, inflation, search trends, or seasonality.

Fully public real MMM datasets are uncommon because marketing spend, sales, promotions, and campaign strategy are commercially sensitive. Therefore, version 1 should not depend on finding a perfect public ASOS-style dataset. Instead, it should be built so that any real dataset matching the schema can be loaded later.

The strongest practical route is:

- Start with a realistic, well-documented demo dataset.
- Add a strict data schema and validation layer.
- Build the analyst dashboard and modeling pipeline around that schema.
- Later plug in real company data, public MMM benchmark data, or user-provided exports without redesigning the product.

## MVP Scope

The first polished version should include:

- Realistic UK fashion ecommerce demo dataset
- Documented schema for replacing the demo data with real data
- Data quality checks
- Exploratory marketing analytics dashboard
- Baseline econometric model
- Bayesian MMM model
- Channel contribution estimates
- ROI and marginal ROI by channel
- Uncertainty intervals
- Budget scenario planner
- Short executive recommendation report

## Out of Scope for Version 1

To keep the project focused, version 1 should not include:

- Full multi-tenant SaaS authentication
- Real ad-platform API integrations
- User-level attribution as a core feature
- Complex customer lifetime value modeling
- Fully automated production retraining
- Enterprise data warehouse integration

These can be part of the future roadmap.

## Success Criteria

The project should be considered successful if it can:

- Generate a realistic marketing dataset for a fashion ecommerce business.
- Explain how each channel contributes to revenue.
- Estimate ROI and marginal ROI with uncertainty.
- Show how adstock, saturation, seasonality, and promotions affect interpretation.
- Recommend a plausible budget reallocation.
- Communicate model assumptions and limitations honestly.
- Look credible to a hiring manager, analyst, consultant, or senior data scientist.

## Suggested Phase 1 Direction

Phase 1 should build the data foundation:

- Define the business scenario.
- Create weekly marketing spend and performance data.
- Add revenue, orders, new customers, AOV, promotions, seasonality, and macro controls.
- Save clean datasets as Parquet or CSV.
- Add validation checks.
- Produce an initial data dictionary.
 - Design the import schema so real data can replace demo data later.

The first dataset should be realistic enough that the later MMM results feel believable, not toy-like.

## Portfolio Story

A strong resume/project description could be:

> Built a marketing effectiveness lab for a UK fashion ecommerce retailer using econometrics, Bayesian marketing mix modeling, causal validation, and budget optimization. Designed a realistic synthetic data pipeline, estimated channel contribution and ROI under uncertainty, and developed a scenario planner for marketing budget reallocation.

## Future Roadmap

Potential expansion after version 1:

- Real data connector templates
- Geo-experiment calibration
- Multi-market modeling
- Profit-aware optimization
- Customer cohort analysis
- MMM vs MTA comparison module
- Tenant-aware SaaS architecture
- Audit logs and secure model run history
- Executive PDF export
- Deployment on cloud infrastructure
