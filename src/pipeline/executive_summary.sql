-- GenAI step: ai_query (through the Unity Gateway model service) writes the monthly executive narrative.
-- Only the 3 latest months are summarized, so the cost stays negligible.
-- A refresh recomputes the whole table: same inputs, same rows, no duplicates.
-- failOnError => false keeps the pipeline green; a template narrative is used and flagged in `model`.
CREATE OR REFRESH MATERIALIZED VIEW gold.executive_summary (
  period STRING NOT NULL,
  headline STRING,
  narrative STRING,
  model STRING,
  CONSTRAINT executive_summary_pk PRIMARY KEY (period)
) AS
WITH top_customers AS (
  SELECT concat_ws('; ', collect_list(concat(customer_name, ' (', segment, ', ', region, ') revenue ', CAST(round(revenue) AS STRING)))) AS top3,
         round(100 * try_divide(sum(revenue), (SELECT sum(revenue) FROM gold.customer_revenue)), 1) AS top3_share_pct
  FROM gold.customer_revenue WHERE revenue_rank <= 3
), k AS (
  SELECT k.*, t.top3, t.top3_share_pct
  FROM gold.kpi_summary k CROSS JOIN top_customers t
  ORDER BY k.period DESC LIMIT 3
), r AS (
  SELECT k.*, ai_query('${llm_endpoint}', concat(
    'You are the analyst of ACME Corp, a retail and consumer goods company. Write a 3 sentence executive summary for leadership, plain text, no markdown, no bullet points. ',
    'Cover revenue, margin and the customer base, and end with one action. Use only these facts. ',
    'Month: ', period, '. Revenue: ', CAST(revenue AS STRING), '. Margin: ', CAST(margin AS STRING), ' (', CAST(margin_pct AS STRING), '%). ',
    'Orders: ', CAST(orders AS STRING), '. Active customers: ', CAST(active_customers AS STRING), '. Average order value: ', CAST(avg_order_value AS STRING), '. ',
    'Revenue change vs prior month: ', CAST(revenue_mom_pct AS STRING), '%. ',
    'Top 3 customers all time: ', top3, ', together ', CAST(top3_share_pct AS STRING), '% of revenue.'),
    failOnError => false) AS ai
  FROM k
)
SELECT period,
       concat('Revenue ', CAST(round(revenue / 1000000, 2) AS STRING), 'M in ', period, ', ',
              IF(revenue_mom_pct >= 0, '+', ''), CAST(revenue_mom_pct AS STRING), '% vs prior month, margin ', CAST(margin_pct AS STRING), '%') AS headline,
       coalesce(ai.result,
                concat('Revenue was ', CAST(revenue AS STRING), ' with ', CAST(orders AS STRING), ' orders from ', CAST(active_customers AS STRING), ' customers.')) AS narrative,
       IF(ai.result IS NULL, 'template', '${llm_endpoint}') AS model
FROM r;
