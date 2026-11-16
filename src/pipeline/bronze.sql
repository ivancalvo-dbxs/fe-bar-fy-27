-- Bronze: incrementally ingest synthetic parquet files with Auto Loader.

CREATE OR REFRESH STREAMING TABLE bronze.customers_incremental AS
SELECT *, _metadata.file_path AS _source_file, current_timestamp() AS _ingested_at
FROM STREAM read_files('${volume_path}/customers', format => 'parquet');

CREATE OR REFRESH STREAMING TABLE bronze.products_incremental AS
SELECT *, _metadata.file_path AS _source_file, current_timestamp() AS _ingested_at
FROM STREAM read_files('${volume_path}/products', format => 'parquet');

CREATE OR REFRESH STREAMING TABLE bronze.stores_incremental AS
SELECT *, _metadata.file_path AS _source_file, current_timestamp() AS _ingested_at
FROM STREAM read_files('${volume_path}/stores', format => 'parquet');

CREATE OR REFRESH STREAMING TABLE bronze.promotions_incremental AS
SELECT *, _metadata.file_path AS _source_file, current_timestamp() AS _ingested_at
FROM STREAM read_files('${volume_path}/promotions', format => 'parquet');

CREATE OR REFRESH STREAMING TABLE bronze.orders_incremental AS
SELECT *, _metadata.file_path AS _source_file, current_timestamp() AS _ingested_at
FROM STREAM read_files('${volume_path}/orders', format => 'parquet');

CREATE OR REFRESH STREAMING TABLE bronze.order_items_incremental AS
SELECT *, _metadata.file_path AS _source_file, current_timestamp() AS _ingested_at
FROM STREAM read_files('${volume_path}/order_items', format => 'parquet');
