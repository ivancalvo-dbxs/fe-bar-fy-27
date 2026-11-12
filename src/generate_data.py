# Databricks notebook source
"""Generate a synthetic retail/CPG dataset for ACME Corp into the bronze volume.

Deterministic (seeded) and idempotent: every run overwrites the same folders.
Story: a growing business, 80/20 customer skew, and promotions that lift unit sales.
"""
from pyspark.sql import SparkSession

N_CUSTOMERS, N_PRODUCTS, N_STORES, N_PROMOS, N_ORDERS = 8000, 300, 24, 14, 150_000
DAYS = 669  # 2025-01-01 .. 2026-10-31
CATEGORIES = ["Beverages", "Snacks", "Personal Care", "Household", "Frozen", "Travel Essentials"]
REGIONS = ["NA", "EMEA", "APAC", "LATAM"]


def arr(values):
    return "array(" + ",".join(f"'{v}'" for v in values) + ")"


def pick(values, seed):
    return f"element_at({arr(values)}, 1 + int(rand({seed}) * {len(values)}))"


def main():
    base = f"/Volumes/{dbutils.widgets.get('catalog')}/bronze/raw_synthetic"  # noqa: F821 (notebook global)
    spark = SparkSession.builder.getOrCreate()

    def write(df, name):
        df.write.mode("overwrite").parquet(f"{base}/{name}")
        print(name, spark.read.parquet(f"{base}/{name}").count())

    write(spark.range(1, N_CUSTOMERS + 1).selectExpr(
        "id AS customer_id",
        f"concat({pick(['Harbor', 'Summit', 'Maple', 'Cedar', 'Blue Ridge', 'Sunrise', 'Coastal', 'Prairie', 'Urban', 'Golden'], 1)},"
        f" ' ', {pick(['Grocers', 'Markets', 'Travel Retail', 'Duty Free', 'Pharmacies', 'Outlets', 'Cash and Carry', 'Convenience'], 2)},"
        " ' #', lpad(id, 5, '0')) AS customer_name",
        "CASE WHEN rand(3) < 0.1 THEN 'Enterprise' WHEN rand(4) < 0.4 THEN 'Mid-Market' ELSE 'SMB' END AS segment",
        "CASE WHEN rand(5) < 0.4 THEN 'NA' WHEN rand(6) < 0.5 THEN 'EMEA' WHEN rand(7) < 0.67 THEN 'APAC' ELSE 'LATAM' END AS region",
    ), "customers")

    write(spark.range(1, N_PRODUCTS + 1).selectExpr(
        "id AS product_id",
        f"{pick(CATEGORIES, 11)} AS category",
        "concat('ACME Brand ', 1 + int(rand(12) * 12)) AS brand",
        "round(1.5 * exp(rand(13) * ln(40)), 2) AS unit_price",  # log-uniform 1.5 .. 60
        "round(1.5 * exp(rand(13) * ln(40)) * (0.45 + rand(14) * 0.3), 2) AS unit_cost",
    ).selectExpr("*", "concat(category, ' item ', lpad(product_id, 3, '0')) AS product_name"), "products")

    write(spark.range(1, N_STORES + 1).selectExpr(
        "id AS store_id",
        "concat('Store ', lpad(id, 2, '0')) AS store_name",
        f"element_at({arr(['Online', 'Retail', 'Wholesale', 'Travel Retail'])}, 1 + int(id % 4)) AS channel",
        f"element_at({arr(REGIONS)}, 1 + int(id % 4)) AS region",
    ), "stores")

    write(spark.range(1, N_PROMOS + 1).selectExpr(
        "id AS promotion_id",
        f"element_at({arr(CATEGORIES)}, 1 + int((id - 1) % 6)) AS category",
        "CAST(10 + 5 * (id % 5) AS INT) AS discount_pct",
        "date_add(DATE'2025-01-01', int(id * 45)) AS start_date",
    ).selectExpr("*", "date_add(start_date, 13) AS end_date",
                 "concat(category, ' ', discount_pct, 'pct promo ', promotion_id) AS promotion_name"), "promotions")

    # Orders: customers skewed 80/20, more orders later in the period (growth)
    write(spark.range(1, N_ORDERS + 1).selectExpr(
        "id AS order_id",
        f"1 + int({N_CUSTOMERS} * pow(rand(21), 2.2)) AS customer_id",
        f"1 + int({N_STORES} * pow(rand(22), 1.3)) AS store_id",
        f"date_add(DATE'2025-01-01', int({DAYS} * pow(rand(23), 0.7))) AS order_date",
        "CASE WHEN rand(24) < 0.97 THEN 'completed' ELSE 'cancelled' END AS status",
    ), "orders")

    spark.read.parquet(f"{base}/orders").createOrReplaceTempView("o")
    spark.read.parquet(f"{base}/products").createOrReplaceTempView("p")
    spark.read.parquet(f"{base}/promotions").createOrReplaceTempView("pr")
    lines = spark.sql(f"""
        WITH l AS (
          SELECT o.order_id, o.order_date, explode(sequence(1, 1 + int(pow(rand(31), 2) * 5))) AS line_no
          FROM o)
        SELECT order_id, line_no,
               1 + int({N_PRODUCTS} * pow(rand(32), 1.8)) AS product_id,
               order_date,
               1 + int(rand(33) * 4) AS base_qty
        FROM l""")
    lines.createOrReplaceTempView("l2")
    write(spark.sql("""
        SELECT l2.order_id, l2.line_no, l2.product_id,
               -- promo active for the product category on the order date: ~80% of lines buy double
               CASE WHEN pr.promotion_id IS NOT NULL AND rand(34) < 0.8 THEN l2.base_qty * 2 ELSE l2.base_qty END AS quantity,
               p.unit_price, p.unit_cost,
               pr.promotion_id, coalesce(pr.discount_pct, 0) AS discount_pct
        FROM l2 JOIN p ON p.product_id = l2.product_id
        LEFT JOIN pr ON pr.category = p.category AND l2.order_date BETWEEN pr.start_date AND pr.end_date
    """), "order_items")


main()
