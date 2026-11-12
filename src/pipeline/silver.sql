-- Silver: conformed entities and the order line fact (completed orders only).
CREATE OR REFRESH MATERIALIZED VIEW silver.customers (
  customer_id BIGINT NOT NULL,
  customer_name STRING,
  segment STRING,
  region STRING,
  CONSTRAINT valid_segment EXPECT (segment IN ('Enterprise', 'Mid-Market', 'SMB')) ON VIOLATION DROP ROW,
  CONSTRAINT customers_pk PRIMARY KEY (customer_id)
) AS
SELECT customer_id, customer_name, segment, region FROM bronze.customers;

CREATE OR REFRESH MATERIALIZED VIEW silver.products (
  product_id BIGINT NOT NULL,
  product_name STRING,
  category STRING,
  brand STRING,
  unit_price DOUBLE,
  unit_cost DOUBLE,
  CONSTRAINT positive_price EXPECT (unit_price > 0) ON VIOLATION DROP ROW,
  CONSTRAINT products_pk PRIMARY KEY (product_id)
) AS
SELECT product_id, product_name, category, brand, unit_price, unit_cost FROM bronze.products;

CREATE OR REFRESH MATERIALIZED VIEW silver.promotions (
  promotion_id BIGINT NOT NULL,
  promotion_name STRING,
  category STRING,
  discount_pct INT,
  start_date DATE,
  end_date DATE,
  CONSTRAINT valid_window EXPECT (end_date >= start_date) ON VIOLATION DROP ROW,
  CONSTRAINT promotions_pk PRIMARY KEY (promotion_id)
) AS
SELECT promotion_id, promotion_name, category, discount_pct, start_date, end_date FROM bronze.promotions;

CREATE OR REFRESH MATERIALIZED VIEW silver.order_lines (
  order_id BIGINT NOT NULL,
  line_no INT NOT NULL,
  order_date DATE,
  customer_id INT,
  product_id INT,
  store_id INT,
  channel STRING,
  promotion_id BIGINT,
  quantity INT,
  revenue DOUBLE,
  cost DOUBLE,
  CONSTRAINT positive_quantity EXPECT (quantity > 0) ON VIOLATION DROP ROW,
  CONSTRAINT known_customer EXPECT (customer_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT has_date EXPECT (order_date IS NOT NULL) ON VIOLATION FAIL UPDATE,
  CONSTRAINT order_lines_pk PRIMARY KEY (order_id, line_no)
) AS
SELECT i.order_id, i.line_no, o.order_date, o.customer_id, i.product_id, o.store_id, s.channel, i.promotion_id,
       i.quantity,
       round(i.quantity * i.unit_price * (1 - i.discount_pct / 100.0), 2) AS revenue,
       round(i.quantity * i.unit_cost, 2) AS cost
FROM bronze.order_items i
JOIN bronze.orders o ON o.order_id = i.order_id AND o.status = 'completed'
JOIN bronze.stores s ON s.store_id = o.store_id;
