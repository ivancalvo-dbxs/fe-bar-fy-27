"""Read-only ACME leadership dashboard. All business queries use Lakebase."""
import logging
import os
from pathlib import Path
from time import perf_counter

import psycopg
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from psycopg.rows import dict_row

app = FastAPI(docs_url=None, redoc_url=None)
log = logging.getLogger('uvicorn.error')
client = WorkspaceClient(config=Config())
QUERIES = {
    'kpis': 'SELECT * FROM serving.kpi_summary ORDER BY period DESC LIMIT 2',
    'trend': 'SELECT date, revenue FROM serving.revenue_daily ORDER BY date',
    'top': 'SELECT customer_name, revenue, margin FROM serving.customer_revenue ORDER BY revenue DESC, customer_id LIMIT 10',
    'bottom': 'SELECT customer_name, revenue, margin FROM serving.customer_revenue ORDER BY revenue, customer_id LIMIT 10',
    'products': 'SELECT product_name, revenue, margin_pct FROM serving.product_performance ORDER BY revenue DESC, product_id LIMIT 10',
    'promotions': 'SELECT promotion_name, lift_pct, promo_revenue FROM serving.promotion_lift ORDER BY lift_pct DESC NULLS LAST',
    'summary': 'SELECT * FROM serving.executive_summary ORDER BY period DESC LIMIT 1',
}


@app.get('/')
def index():
    return FileResponse(Path(__file__).with_name('index.html'))


@app.get('/api/dashboard')
def dashboard():
    started = perf_counter()
    try:
        token = client.postgres.generate_database_credential(endpoint=os.environ['LAKEBASE_ENDPOINT']).token
        with psycopg.connect(host=os.environ['PGHOST'], dbname=os.environ['PGDATABASE'],
                             user=os.environ['PGUSER'], password=token, sslmode='require',
                             connect_timeout=10, row_factory=dict_row,
                             options='-c statement_timeout=15000 -c default_transaction_read_only=on') as conn:
            query_start = perf_counter()
            result = {key: conn.execute(sql).fetchall() for key, sql in QUERIES.items()}
            query_ms = round((perf_counter() - query_start) * 1000, 1)
        if not result['kpis']:
            raise HTTPException(503, 'Snapshot is empty. Run the data and sync pipelines.')
        result['query_ms'] = query_ms
        result['total_ms'] = round((perf_counter() - started) * 1000, 1)
        log.info('Lakebase dashboard rows=%s query_ms=%s total_ms=%s',
                 {key: len(result[key]) for key in QUERIES}, query_ms, result['total_ms'])
        return result
    except (psycopg.Error, KeyError) as exc:
        log.error('Lakebase dashboard unavailable: %s', type(exc).__name__)
        raise HTTPException(503, 'Lakebase snapshot unavailable. Try again shortly.') from exc


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=int(os.environ.get('DATABRICKS_APP_PORT', '8000')))
