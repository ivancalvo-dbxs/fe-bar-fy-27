"""Exercise HTTP behavior and execute ranking SQL on deterministic fixtures."""
import importlib.util
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import psycopg
import pytest
from fastapi.testclient import TestClient

with patch('databricks.sdk.WorkspaceClient'), patch('databricks.sdk.core.Config'):
    spec = importlib.util.spec_from_file_location('dashboard', Path(__file__).parents[1] / 'app/app.py')
    dashboard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dashboard)


@pytest.fixture
def boundary(monkeypatch):
    for key in ['LAKEBASE_ENDPOINT', 'PGHOST', 'PGDATABASE', 'PGUSER']:
        monkeypatch.setenv(key, 'test')
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = [
        {'period': '2026-10', 'revenue': 100, 'active_customers': 4},
    ]
    with patch.object(dashboard.psycopg, 'connect') as connect:
        connect.return_value.__enter__.return_value = conn
        yield TestClient(dashboard.app), conn, connect


def test_routes_and_read_only_boundary(boundary):
    client, conn, connect = boundary
    assert 'ACME CORP' in client.get('/').text
    response = client.get('/api/dashboard')
    assert response.status_code == 200
    assert set(dashboard.QUERIES) <= response.json().keys()
    assert 'default_transaction_read_only=on' in connect.call_args.kwargs['options']
    conn.execute.return_value.fetchall.return_value = []
    assert client.get('/api/dashboard').status_code == 503
    connect.side_effect = psycopg.OperationalError('private connection details')
    response = client.get('/api/dashboard')
    assert response.status_code == 503
    assert 'private' not in response.text


@pytest.mark.parametrize('revenue,customers,expected', [
    (100, 4, 25), (100, 0, None), (100, None, None), (None, 4, None), (0, 4, 0),
])
def test_revenue_per_customer(boundary, revenue, customers, expected):
    client, conn, _ = boundary
    conn.execute.return_value.fetchall.return_value = [
        {'revenue': revenue, 'active_customers': customers},
    ]
    response = client.get('/api/dashboard')
    assert response.status_code == 200
    assert response.json()['kpis'][0]['revenue_per_customer'] == expected


@pytest.mark.parametrize('key', ['LAKEBASE_ENDPOINT', 'PGHOST', 'PGDATABASE', 'PGUSER'])
def test_missing_environment(boundary, monkeypatch, key):
    client, _, connect = boundary
    monkeypatch.delenv(key)
    response = client.get('/api/dashboard')
    assert response.status_code == 503
    assert response.json() == {'detail': 'Lakebase snapshot unavailable. Try again shortly.'}
    connect.assert_not_called()


@pytest.mark.parametrize('query,expected', [
    ('top', ['Alpha', 'Beta', 'Low', 'Unknown']),
    ('bottom', ['Low', 'Alpha', 'Beta', 'Unknown']),
    ('products', ['Alpha', 'Beta', 'Low', 'Unknown']),
    ('promotions', ['Alpha', 'Beta', 'Low', 'Unknown']),
])
def test_rankings(query, expected):
    with sqlite3.connect(':memory:') as conn:
        conn.execute("ATTACH DATABASE ':memory:' AS serving")
        conn.execute('CREATE TABLE serving.customer_revenue (customer_id, customer_name, revenue)')
        conn.execute('CREATE TABLE serving.product_performance (product_id, product_name, revenue, margin_pct)')
        conn.execute('CREATE TABLE serving.promotion_lift (promotion_id, promotion_name, lift_pct)')
        rows = [(4, 'Unknown', None), (2, 'Beta', 100), (3, 'Low', 10), (1, 'Alpha', 100)]
        conn.executemany('INSERT INTO serving.customer_revenue VALUES (?, ?, ?)', rows)
        conn.executemany('INSERT INTO serving.product_performance VALUES (?, ?, ?, 12.3)', rows)
        conn.executemany('INSERT INTO serving.promotion_lift VALUES (?, ?, ?)', rows)
        assert [row[0] for row in conn.execute(dashboard.QUERIES[query])] == expected


def test_grant_script_import_has_no_side_effects():
    spec = importlib.util.spec_from_file_location('grant_app', Path(__file__).parents[1] / 'scripts/grant_app.py')
    module = importlib.util.module_from_spec(spec)
    with patch('subprocess.check_output') as cli, patch('psycopg.connect') as connect:
        spec.loader.exec_module(module)
    cli.assert_not_called()
    connect.assert_not_called()
    assert callable(module.main)
