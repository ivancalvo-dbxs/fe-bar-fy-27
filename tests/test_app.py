"""Exercise the real HTTP routes with a fake database boundary."""
import importlib.util
from pathlib import Path
from unittest.mock import MagicMock, patch

import psycopg
from fastapi.testclient import TestClient

with patch('databricks.sdk.WorkspaceClient'), patch('databricks.sdk.core.Config'):
    spec = importlib.util.spec_from_file_location('dashboard', Path(__file__).parents[1] / 'app/app.py')
    dashboard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dashboard)


def test_routes_and_read_only_boundary(monkeypatch):
    for key in ['LAKEBASE_ENDPOINT', 'PGHOST', 'PGDATABASE', 'PGUSER']:
        monkeypatch.setenv(key, 'test')
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = [{'period': '2026-10'}]
    with patch.object(dashboard.psycopg, 'connect') as connect:
        connect.return_value.__enter__.return_value = conn
        client = TestClient(dashboard.app)
        assert 'ACME CORP' in client.get('/').text
        response = client.get('/api/dashboard')
        assert response.status_code == 200
        assert set(dashboard.QUERIES) <= response.json().keys()
        assert 'default_transaction_read_only=on' in connect.call_args.kwargs['options']
        assert all(q.startswith('SELECT ') and 'serving.' in q for q in dashboard.QUERIES.values())
        conn.execute.return_value.fetchall.return_value = []
        assert client.get('/api/dashboard').status_code == 503
        connect.side_effect = psycopg.OperationalError('private connection details')
        response = client.get('/api/dashboard')
        assert response.status_code == 503
        assert 'private' not in response.text
