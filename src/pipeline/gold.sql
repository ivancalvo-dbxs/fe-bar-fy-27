-- Gold: the app contract. Each table has a NOT NULL primary key so Lakebase can sync it.
CREATE OR REFRESH MATERIALIZED VIEW gold.customer_revenue (
  customer_id BIGINT NOT NULL,
  customer_name STRING,
  segment STRING,
  region STRING,
  orders BIGINT,
  revenue DOUBLE,
  margin DOUBLE,
  revenue_rank INT,
  CONSTRAINT customer_revenue_pk PRIMARY KEY (customer_id)
) AS
SELECT c.customer_id, c.customer_name, c.segment, c.region,
       count(DISTINCT l.order_id) AS orders,
       round(sum(l.revenue), 2) AS revenue,
       round(sum(l.revenue - l.cost), 2) AS margin,
       CAST(rank() OVER (ORDER BY sum(l.revenue) DESC) AS INT) AS revenue_rank
FROM silver.customers c JOIN silver.order_lines l USING (customer_id)
GROUP BY c.customer_id, c.customer_name, c.segment, c.region;

CREATE OR REFRESH MATERIALIZED VIEW gold.revenue_daily (
  date DATE NOT NULL,
  revenue DOUBLE,
  margin DOUBLE,
  orders BIGINT,
  CONSTRAINT revenue_daily_pk PRIMARY KEY (date)
) AS
SELECT order_date AS date, round(sum(revenue), 2) AS revenue, round(sum(revenue - cost), 2) AS margin,
       count(DISTINCT order_id) AS orders
FROM silver.order_lines GROUP BY order_date;

CREATE OR REFRESH MATERIALIZED VIEW gold.product_performance (
  product_id BIGINT NOT NULL,
  product_name STRING,
  category STRING,
  brand STRING,
  units BIGINT,
  revenue DOUBLE,
  margin DOUBLE,
  margin_pct DOUBLE,
  revenue_rank INT,
  CONSTRAINT product_performance_pk PRIMARY KEY (product_id)
) AS
SELECT p.product_id, p.product_name, p.category, p.brand,
       sum(l.quantity) AS units,
       round(sum(l.revenue), 2) AS revenue,
       round(sum(l.revenue - l.cost), 2) AS margin,
       round(100 * try_divide(sum(l.revenue - l.cost), sum(l.revenue)), 1) AS margin_pct,
       CAST(rank() OVER (ORDER BY sum(l.revenue) DESC) AS INT) AS revenue_rank
FROM silver.products p JOIN silver.order_lines l USING (product_id)
GROUP BY p.product_id, p.product_name, p.category, p.brand;

-- Lift = promo-window daily revenue of the promoted category vs its 28 days before the promo.
CREATE OR REFRESH MATERIALIZED VIEW gold.promotion_lift (
  promotion_id BIGINT NOT NULL,
  promotion_name STRING,
  category STRING,
  discount_pct INT,
  start_date DATE,
  end_date DATE,
  promo_revenue DOUBLE,
  promo_margin DOUBLE,
  promo_daily_revenue DOUBLE,
  baseline_daily_revenue DOUBLE,
  lift_pct DOUBLE,
  CONSTRAINT promotion_lift_pk PRIMARY KEY (promotion_id)
) AS
WITH cat_daily AS (
  SELECT p.category, l.order_date, sum(l.revenue) AS revenue, sum(l.revenue - l.cost) AS margin
  FROM silver.order_lines l JOIN silver.products p USING (product_id)
  GROUP BY p.category, l.order_date
), agg AS (
  SELECT pr.*,
         sum(IF(d.order_date BETWEEN pr.start_date AND pr.end_date, d.revenue, 0)) AS promo_revenue,
         sum(IF(d.order_date BETWEEN pr.start_date AND pr.end_date, d.margin, 0)) AS promo_margin,
         sum(IF(d.order_date >= date_sub(pr.start_date, 28) AND d.order_date < pr.start_date, d.revenue, 0)) AS base_revenue
  FROM silver.promotions pr JOIN cat_daily d ON d.category = pr.category
  GROUP BY pr.promotion_id, pr.promotion_name, pr.category, pr.discount_pct, pr.start_date, pr.end_date
)
SELECT promotion_id, promotion_name, category, discount_pct, start_date, end_date,
       round(promo_revenue, 2) AS promo_revenue,
       round(promo_margin, 2) AS promo_margin,
       round(promo_revenue / (datediff(end_date, start_date) + 1), 2) AS promo_daily_revenue,
       round(base_revenue / 28, 2) AS baseline_daily_revenue,
       round(100 * (try_divide(promo_revenue / (datediff(end_date, start_date) + 1), base_revenue / 28) - 1), 1) AS lift_pct
FROM agg;

-- One row per month; the executive summary reads this table.
CREATE OR REFRESH MATERIALIZED VIEW gold.kpi_summary (
  period STRING NOT NULL,
  revenue DOUBLE,
  margin DOUBLE,
  margin_pct DOUBLE,
  orders BIGINT,
  active_customers BIGINT,
  avg_order_value DOUBLE,
  revenue_mom_pct DOUBLE,
  CONSTRAINT kpi_summary_pk PRIMARY KEY (period)
) AS
WITH m AS (
  SELECT date_format(order_date, 'yyyy-MM') AS period, sum(revenue) AS revenue, sum(revenue - cost) AS margin,
         count(DISTINCT order_id) AS orders, count(DISTINCT customer_id) AS active_customers
  FROM silver.order_lines GROUP BY 1
)
SELECT period, round(revenue, 2) AS revenue, round(margin, 2) AS margin,
       round(100 * try_divide(margin, revenue), 1) AS margin_pct, orders, active_customers,
       round(try_divide(revenue, orders), 2) AS avg_order_value,
       round(100 * (try_divide(revenue, lag(revenue) OVER (ORDER BY period)) - 1), 1) AS revenue_mom_pct
FROM m;
