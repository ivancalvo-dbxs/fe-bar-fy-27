# Serving layer operations

The bundle owns one dedicated Lakebase Autoscaling project, six snapshot synced tables, a curated Genie space and a Python FastAPI app.
Genie alone uses a SQL warehouse; all app business queries use Lakebase.
The project uses its automatically created production branch and databricks_postgres database, dedicated to this app.

```sh
export BUNDLE_VAR_catalog=your_existing_catalog
databricks bundle validate --strict -t dev --profile ivan-febar
databricks bundle deploy -t dev --profile ivan-febar
# Wait for all six postgres get-synced-table statuses to be ONLINE.
# Install app/requirements.txt in your local virtual environment first.
python scripts/grant_app.py --profile ivan-febar
databricks bundle run leadership -t dev --profile ivan-febar
```

The app name defaults to the current user's domain-friendly name with an ACME prefix.
If it exceeds 30 characters or collides, set an uncommitted app_name override in `.databricks/bundle/dev/variable-overrides.json`.
The Genie warehouse is looked up by display name; override genie_warehouse for another existing warehouse.
No workspace-specific identifiers are stored in source control.

Snapshot mode deliberately avoids continuous compute for this synthetic demonstration.
Refresh view reloads the existing Lakebase copy and does not refresh the snapshot.
To refresh after the data pipeline runs, get each synced table's pipeline_id with `databricks postgres get-synced-table synced_tables/<catalog>.serving.<table> --profile ivan-febar`, then run `databricks pipelines start-update <pipeline_id> --profile ivan-febar` and wait for ONLINE again.
Run grant_app.py after new tables or app resource changes.
The platform attachment initially grants CONNECT and CREATE; grant_app.py revokes database CREATE and grants only schema USAGE and SELECT on the six explicit tables.
No UC privileges or warehouse access are granted to the app principal.

KPIs show the latest available month beside the prior month's value.
Customer and product rankings cover all periods; monthly distinct customers must never be summed.
Revenue per customer means monthly revenue divided by monthly active customers.
Promotion lift is descriptive category daily revenue versus the preceding 28-day baseline, not a causal estimate.
Executive summaries are generated upstream through Unity Gateway, copied into Lakebase, labeled AI-generated and displayed with their own period and model.
A fresh OAuth database credential is generated for every dashboard request; connections close after the seven bounded SELECT queries.
This favors simple credential rotation over connection reuse for this small leadership dashboard.

Verification uses text output from the app JSON endpoint, app logs, sync status, Postgres row counts and Genie conversation query results.
The dashboard logs row counts and query/total latency without logging customer records or credentials.
One HTTP boundary test covers the page, success payload, read-only connection, empty snapshot and redacted database error.
