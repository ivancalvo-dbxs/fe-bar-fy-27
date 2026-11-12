-- Bronze: 1:1 copies of the synthetic parquet files.
-- Materialized views (batch read_files) so a regenerated dataset replaces, never duplicates, the data.

CREATE OR REFRESH MATERIALIZED VIEW bronze.customers AS
SELECT *, _metadata.file_path AS _source_file, current_timestamp() AS _ingested_at
FROM read_files('${volume_path}/customers', format => 'parquet');

CREATE OR REFRESH MATERIALIZED VIEW bronze.products AS
SELECT *, _metadata.file_path AS _source_file, current_timestamp() AS _ingested_at
FROM read_files('${volume_path}/products', format => 'parquet');

CREATE OR REFRESH MATERIALIZED VIEW bronze.stores AS
SELECT *, _metadata.file_path AS _source_file, current_timestamp() AS _ingested_at
FROM read_files('${volume_path}/stores', format => 'parquet');

CREATE OR REFRESH MATERIALIZED VIEW bronze.promotions AS
SELECT *, _metadata.file_path AS _source_file, current_timestamp() AS _ingested_at
FROM read_files('${volume_path}/promotions', format => 'parquet');

CREATE OR REFRESH MATERIALIZED VIEW bronze.orders AS
SELECT *, _metadata.file_path AS _source_file, current_timestamp() AS _ingested_at
FROM read_files('${volume_path}/orders', format => 'parquet');

CREATE OR REFRESH MATERIALIZED VIEW bronze.order_items AS
SELECT *, _metadata.file_path AS _source_file, current_timestamp() AS _ingested_at
FROM read_files('${volume_path}/order_items', format => 'parquet');
