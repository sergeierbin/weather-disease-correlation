# Shared database connection for all ingestion scripts.
# Credentials are read from environment variables set in .env (local)
# or passed via docker-compose.yml environment block (inside containers).

import os
import psycopg2
import psycopg2.extras


def get_connection():
    # POSTGRES_PORT is optional — defaults to 5432 if not set
    return psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ.get("POSTGRES_PORT", 5432)),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )


def execute_values(conn, sql, rows):
    # execute_values sends all rows in a single round-trip, much faster than
    # calling cursor.execute() in a loop for large datasets
    with conn.cursor() as cur:
        psycopg2.extras.execute_values(cur, sql, rows)
    conn.commit()
