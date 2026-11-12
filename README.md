# ACME RCT analytics accelerator on Databricks

A Databricks Asset Bundle that takes synthetic retail and consumer goods data from a job to a leadership app, using only Databricks-native services.
Serving details and the refresh runbook are in [SERVING.md](SERVING.md).

> **Privacy and scope notice.**
> The business context behind this project is internal and confidential.
> The real partner name is replaced by the fictional **ACME Corp**, and named prospects stay as REDACTED_1 and REDACTED_2.
> All data is synthetic, and the repo contains no workspace URLs, e-mails, IDs or tokens.
> The sizing in the business context ($15K commit, $180K+ benchmark) and any onboarding or go-live timing are directional and not customer-confirmed.

## Built with Unity Gateway

This project was developed using the Unity Gateway ([UG repository](https://github.com/databricks/unity-gateway)).
The executive summary calls a gateway model service (`system.ai.claude-haiku-5-5`) through `ai_query`, so model access, permissions and governance stay in Unity Catalog.
In this repo the gateway is used in `src/pipeline/executive_summary.sql`, and the service name comes from the `llm_endpoint` variable in `databricks.yml`.
The name was discovered with the CLI command `databricks ai-gateway list-model-services --parent schemas/system.ai`.
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
| 5 | Genie | Curated space over gold | Ad hoc questions with curated sample questions |
| 6 | App | FastAPI app | KPI strip, revenue trend, top and bottom customers, products, promotion lift, AI summary |

Single source of truth rule: the app queries only Lakebase, never Unity Catalog tables or a SQL warehouse.
The platform attachment grants the app principal CONNECT, then `scripts/grant_app.py` revokes database CREATE and grants SELECT on the six tables only.

```
Job -> Volume -> SDP bronze/silver/gold -> ai_query summary
                                  \-> Genie space
gold (6 tables) -> synced tables -> Lakebase -> App
```

## Measured results

All numbers are self-reported from runs on a real workspace with synthetic data.
Run logs are not committed, to keep the repo small, and every count can be reproduced with the commands under Run it.

| Measure | Result |
|---------|--------|
| Source rows | 150,000 orders, 337,674 order items, 8,000 customers, 300 products |
| Gold rows | customer_revenue 8,000, revenue_daily 669, product_performance 300, promotion_lift 14, kpi_summary 22, executive_summary 3 |
| Runtimes | data job 37 s; pipeline 81 to 90 s end to end on serverless |
| AI summary | 3 rows in 12 to 14 s, about 4 s per row |
| Snapshot sync | 6 of 6 tables ONLINE, row counts equal gold, 5.9 to 8.0 s each |
| Lakebase queries | 7 queries per page load, 31.1 ms total (33.6 to 34.1 ms before UI hardening) |
| App latency | handler 143.9 ms, full HTTP request 743 ms including per-request OAuth |
| App tests | 15 collected cases, all passing; DOM checks at desktop and mobile widths |
| Genie checks | revenue per customer $176.32; top customer $219,740.03; best promotion lift 137.2% |
| Reruns | identical counts on a second run; SELECT grants survived a snapshot refresh |

## What leadership learns from the app

Read from the deployed app for October 2026.
The data is synthetic, so the point is the kind of decision it supports, not the values.

| Signal in the app | Reading | Decision it supports |
|-------------------|---------|----------------------|
| Revenue $845,969 vs $822,822 prior month | +2.8% | Growth is on track |
| Orders 9,598 vs 9,082 | +5.7%, so average order value fell from about $90.6 to $88.1 | Growth is volume, not basket size: test bundling and upsell |
| Active customers 4,798 vs 4,725, revenue per customer $176 vs $174 | +1.5% and +1% | The base grows slowly and value per customer barely moves |
| Top customer $219,740, second $79,540; bottom 10 earn $14 to $58 | Top is 2.8x the runner-up; a long tail of low-value accounts | Protect key accounts, run activation offers for the tail |
| Product margin 25.6% (top seller) vs 48.4% (#5 seller) | A 22.8 point spread among the top 10 | Steer the mix toward high-margin items, not just revenue |
| Promotion lift: discounts of 15% or less lift 51% to 137%, 30% discounts lift 32% to 34% | Deeper discounts did not lift more | Cut discount depth first (descriptive, not causal) |

Trade promotion pricing, demand planning and shopper insights are the accelerators that act on these signals.
The app is what clients can buy on Databricks paper, with consumption counting toward the $15K commit.
These synthetic values do not validate the $180K+ benchmark.

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
The work landed as PRs #1 to #4.
Cursor's FAIL on PR #1 claimed `ai_query` returns `.response`, and a live `typeof` query showed it returns `.result`, so the finding was rejected while its `try_divide` and stable-ordering suggestions were applied.
Claude Code's PASS on the serving PR came with 12 notes, and the key ones (grant persistence, UI formatting, null guards, tests) were applied.
Prompts and agent transcripts are not committed.
Humans merge; agents only open PRs.

## Run it

```sh
export BUNDLE_VAR_catalog=your_existing_catalog
databricks bundle validate --strict -t dev --profile <profile>
databricks bundle deploy -t dev --profile <profile>
databricks bundle run -t dev --profile <profile> <job_or_pipeline>
```

See SERVING.md for the grants step and the app start.
