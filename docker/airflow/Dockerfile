FROM apache/airflow:2.9.3-python3.11

USER airflow
RUN pip install --no-cache-dir \
    psycopg2-binary==2.9.9 \
    requests==2.31.0 \
    dbt-core==1.8.6 \
    dbt-postgres==1.8.2 \
    meteostat==1.6.8
