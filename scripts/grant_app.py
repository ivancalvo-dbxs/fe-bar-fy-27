"""Run after bundle deploy and ONLINE syncs: python scripts/grant_app.py --profile NAME --target TARGET."""
import argparse
import json
import subprocess

import psycopg
from psycopg import sql


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', required=True)
    parser.add_argument('--target', required=True)
    args = parser.parse_args()

    def cli(*parts):
        return json.loads(subprocess.check_output([
            'databricks', *parts, '--profile', args.profile, '-o', 'json',
        ]))

    bundle = cli('bundle', 'validate', '-t', args.target)
    project = bundle['resources']['postgres_projects']['serving']['project_id']
    app = cli('apps', 'get', bundle['resources']['apps']['leadership']['name'])
    endpoint = f'projects/{project}/branches/production/endpoints/primary'
    host = cli('postgres', 'get-endpoint', endpoint)['status']['hosts']['host']
    token = cli('postgres', 'generate-database-credential', endpoint)['token']
    user = cli('current-user', 'me')['userName']
    role = sql.Identifier(app['service_principal_client_id'])
    with psycopg.connect(host=host, dbname='databricks_postgres', user=user, password=token, sslmode='require') as conn:
        conn.execute(sql.SQL('GRANT USAGE ON SCHEMA serving TO {}').format(role))
        for table in bundle['resources']['postgres_synced_tables']:
            conn.execute(sql.SQL('GRANT SELECT ON serving.{} TO {}').format(sql.Identifier(table), role))
        # The platform attachment grants CREATE; this read-only app needs CONNECT only.
        conn.execute(sql.SQL('REVOKE CREATE ON DATABASE databricks_postgres FROM {}').format(role))
    print('Granted schema usage and SELECT on the six synced tables; revoked database CREATE.')


if __name__ == '__main__':
    main()
