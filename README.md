# ACME RCT analytics accelerator on Databricks

A Databricks Asset Bundle that takes synthetic retail and consumer goods data from a job to a leadership app, using only Databricks-native services.
Serving details and the refresh runbook are in [SERVING.md](SERVING.md).

> **Privacy and scope notice.**
> The business context behind this project is internal and confidential.
> The real partner name is replaced by the fictional **ACME Corp**, and named prospects stay as REDACTED_1 and REDACTED_2.
> All data is synthetic, and the repo contains no workspace URLs, e-mails, IDs or tokens.
> Sizing, onboarding and go-live dates are directional and not customer-confirmed.

## Built with Unity Gateway

This project was developed using the Unity Gateway ([UG repository](https://github.com/databricks/unity-gateway)).
The executive summary calls a gateway model service (`system.ai.claude-haiku-5-5`) through `ai_query`, so model access, permissions and governance stay in Unity Catalog.
The Databricks agent skills (core, DABs, jobs, pipelines, Lakebase, apps, Genie, unity-gateway) were the reference for every resource.

## Business context and impact

ACME's industry teams engage retail, consumer goods and travel (RCT) prospects with Databricks-native accelerator apps: trade promotion pricing, marketing mix, demand planning and shopper insights.
They are built on Genie, Unity Catalog, Lakebase and Unity AI Gateway, and are hosted in ACME's workspace or deployed in the client's workspace.
Databricks delivers Built On validation (a Partner Well-Architected review with an SA) and a Marketplace listing, so clients discover the apps and buy on their existing Databricks paper.

The use case is live when three things are true:
1. Built On validation is passed.
2. The Marketplace listing is published.
3. ACME's development and hosting workspace consumes against the $15K annual commit.

Context, not included in sizing: ACME estimates each enterprise client deployment could drive $180K+ in annual consumption.
This is ACME's own benchmark and is not validated.
Year one is with Databricks, there is no live client yet, and the pipeline includes existing ACME clients such as REDACTED_1 and REDACTED_2.

This repo is the reference journey: the same bundle pattern, parameterised by catalog, can be hosted by ACME or deployed into a client workspace.
The app answers the question leadership asks first: how is the business doing, and what is revenue per customer?

## The journey in six steps

| # | Step | Resource | What it does |
|---|------|----------|--------------|
| 1 | Lakeflow | Job `acme-rct-generate-synthetic-data` | Writes seeded, idempotent parquet (customers, products, stores, promotions, orders, order items) |
| 1 | Lakeflow | SDP pipeline `acme-rct-medallion` | Bronze, silver (with expectations) and gold, serverless SQL |
| 2 | Unity Catalog | Schemas `bronze`, `silver`, `gold`; volume `bronze.raw_synthetic` | Governed storage for raw files and the medallion tables |
| 3 | GenAI | `gold.executive_summary` | `ai_query` over the KPIs through Unity Gateway; template fallback marked `template` |
| 4 | Lakebase | Project plus six synced tables | Gold tables snapshot-synced to Postgres, primary keys from UC constraints |
| 5 | Genie | Curated space over gold | Ad hoc questions with sample queries |
| 6 | App | FastAPI app | KPI strip, revenue trend, top and bottom customers, products, promotion lift, AI summary |

Single source of truth rule: the app queries only Lakebase, never Unity Catalog tables or a SQL warehouse.
Its service principal has CONNECT and explicit SELECT on the six tables, with database CREATE revoked.

```
Job -> Volume -> SDP bronze/silver/gold -> ai_query summary
                                  \-> Genie space
gold (6 tables) -> synced tables -> Lakebase -> App
```

## Measured results

All numbers come from runs on a real workspace with synthetic data.

| Measure | Result |
|---------|--------|
| Source rows | 150,000 orders, 337,674 order items, 8,000 customers, 300 products |
| Silver order lines | 327,535 (completed orders only) |
| Gold rows | customer_revenue 8,000, revenue_daily 669, product_performance 300, promotion_lift 14, kpi_summary 22, executive_summary 3 |
| Data job runtime | 37 s (43 s cold) |
| Pipeline runtime | about 81 to 90 s end to end on serverless |
| AI summary | 3 rows in 12 to 14 s, about 4 s per row |
| Snapshot sync | 6 of 6 tables ONLINE, row counts equal gold, 5.9 to 8.0 s each |
| Lakebase queries | 7 queries per page load, 33.6 to 34.1 ms total |
| App HTTP latency | 720 to 1,109 ms per page, including per-request OAuth |
| Genie checks | latest monthly revenue per customer $176.32; top customer $219,740.03; best promotion lift 137.2% |
| Reruns | a second run gave identical counts (idempotent) |

Sample AI summary, period 2026-10: "October 2026 revenue reached $845,968.61, up 2.8% from the prior month, with a gross margin of $327,952.32 (38.8%)."

## Decisions and trade-offs

- **Bronze as materialized views over `read_files`, not streaming tables.** The job overwrites files, so a stream would ingest duplicates.
- **Catalog passed by variable.** Creating a catalog needs a metastore privilege, so create it once and set `BUNDLE_VAR_catalog`.
- **No `mode: development`.** It would prefix schema names and break the bronze, silver, gold contract.
- **Snapshot sync, not continuous.** It avoids always-on compute for a demo, at the cost of explicit refreshes.
- **Per-request OAuth and no pooling.** Simple credential rotation wins for a small leadership dashboard.
- **Headline computed in SQL, narrative from the model.** Numbers stay deterministic and the model is labelled in the data.
- **A skill doc was wrong, so we tested.** The docs said `ai_query(..., failOnError => false)` returns `.response`, but the runtime returns `.result`; a typeof query settled it.
- **Promotion lift is descriptive,** a category daily revenue versus a 28-day baseline, not a causal estimate.

## How AI built this

A tech-lead agent split the work into three tasks and ran each in its own git worktree with a different vendor's coding agent.
Claude Code built the data layer, Codex built the serving layer, and Cursor and Claude Code cross-reviewed each other's PRs from saved diffs.
One review failure was investigated, disproved with a live query, and the review's cheap hardening items (`try_divide`, stable ordering) were applied.
Humans merge; agents only open PRs.

## Run it

```sh
export BUNDLE_VAR_catalog=your_existing_catalog
databricks bundle validate --strict -t dev --profile <profile>
databricks bundle deploy -t dev --profile <profile>
databricks bundle run -t dev --profile <profile> <job_or_pipeline>
```

See SERVING.md for the grants step and the app start.

## Not covered

Continuous sync, CI, multi-target promotion, and the Built On and Marketplace steps themselves.
