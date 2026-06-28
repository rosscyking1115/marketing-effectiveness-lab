# Phase 7: Real Data Import Workflow

## Objective

Allow the Marketing Effectiveness Lab to work with user-provided weekly marketing data instead of only generated demo data.

This phase adds:

- CSV template generation
- In-app CSV upload
- Schema validation for uploaded data
- Clear validation errors
- In-memory uploaded dataset analysis

## Import Contract

Uploaded data must follow the same weekly schema used by the demo dataset:

- One row per week
- `week_start` must be a Monday date
- Weekly dates must be continuous
- Required columns must be present
- Numeric fields must be numeric
- Spend and volume fields must be non-negative
- Flag fields must be `0` or `1`

The current modeling workflow requires at least 57 weekly rows because it holds out the latest 26 weeks for validation.

## Dashboard Workflow

The sidebar now includes a data source selector:

- Demo data
- Upload CSV

The user can download a CSV template, populate it with real weekly data, and upload it directly through the dashboard.

For this prototype, uploaded files are parsed in memory and are not written to disk.

## Why This Matters

The project is no longer locked to a synthetic dataset. The generated data remains useful for product development and public demo use, but the app can now run on real weekly marketing exports if they match the schema.

This creates a practical route for real-world use:

- Export weekly channel spend from ad platforms
- Export weekly revenue/orders from ecommerce or finance systems
- Add promotion, seasonality, and macro control fields
- Upload the CSV
- Validate and analyze the data

## Future Enhancements

Potential next steps:

- Import mapping UI for differently named columns
- Optional CSV persistence with audit logs
- Data quality scoring
- Warehouse connectors
- Secure user authentication before storing real data
- Tenant-aware storage for multi-brand use
