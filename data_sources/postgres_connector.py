import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
import os
from dotenv import load_dotenv

load_dotenv()
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
db_name = os.getenv("DB_NAME")
db_driver = os.getenv("DB_DRIVER")


def create_postgres_engine():
    database_url = URL.create(drivername=db_driver, username=db_user,
                              password=db_password, host=db_host, port=db_port,
                              database=db_name)

    engine = create_engine(database_url)
    return engine


def load_table(table_name):
    engine = create_postgres_engine()
    query = f"SELECT * FROM {table_name}"
    df = pd.read_sql(query, engine)
    return df


def get_table_names():
    engine = create_postgres_engine()
    query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public' \
            """
    df = pd.read_sql(query, engine)
    return df['table_name'].tolist()


def get_table_columns(table_name):
    engine = create_postgres_engine()
    query = f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}'"
    df = pd.read_sql(query, engine)
    return df['column_name'].tolist()


def get_table_dtypes(table_name):
    engine = create_postgres_engine()
    query = f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table_name}'"
    df = pd.read_sql(query, engine)
    return df.set_index('column_name')['data_type'].to_dict()


def get_table_stats(table_name):
    engine = create_postgres_engine()
    query = f"SELECT column_name, COUNT(*) FROM {table_name} GROUP BY column_name"
    df = pd.read_sql(query, engine)
    return df.set_index('column_name')['COUNT(*)'].to_dict()


def get_table_null_count(table_name):
    engine = create_postgres_engine()
    query = f"SELECT column_name, COUNT(*) FROM {table_name} WHERE {table_name}.column_name IS NULL GROUP BY column_name"
    df = pd.read_sql(query, engine)
    return df.set_index('column_name')['COUNT(*)'].to_dict()


def get_table_distinct_count(table_name, column_name):
    engine = create_postgres_engine()
    query = f"SELECT COUNT(DISTINCT {column_name}) FROM {table_name}"
    return pd.read_sql(query, engine).iloc[0, 0]


def get_table_distinct_values(table_name, column_name):
    engine = create_postgres_engine()
    query = f"SELECT DISTINCT {column_name} FROM {table_name}"
    return pd.read_sql(query, engine)[column_name].tolist()


def get_table_sample(table_name, n=10):
    engine = create_postgres_engine()
    query = f"SELECT * FROM {table_name} LIMIT {n}"
    return pd.read_sql(query, engine)


def get_table_description(table_name):
    engine = create_postgres_engine()
    query = f"SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = '{table_name}'"
    return pd.read_sql(query, engine)


def get_table_size(table_name):
    engine = create_postgres_engine()
    query = f"SELECT pg_size_pretty(pg_total_relation_size('{table_name}'))"
    return pd.read_sql(query, engine).iloc[0, 0]


def get_table_indexes(table_name):
    engine = create_postgres_engine()
    query = f"SELECT indexname, indexdef FROM pg_indexes WHERE tablename = '{table_name}'"
    return pd.read_sql(query, engine)


def get_table_foreign_keys(table_name):
    engine = create_postgres_engine()
    query = f"SELECT conname, confrelid, confkey, confupdtype FROM pg_constraint WHERE conrelid = '{table_name}' AND contype = 'f'"
    return pd.read_sql(query, engine)


def get_table_primary_keys(table_name):
    engine = create_postgres_engine()
    query = f"SELECT a.attname FROM pg_index i JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey) WHERE i.indrelid = '{table_name}' AND i.indisprimary"
    return pd.read_sql(query, engine)


def update_table(table_name, update_values, where_conditions):
    engine = create_postgres_engine()

    set_clause = ", ".join([f"{col} = :set_{col}" for col in update_values.keys()])
    where_clause = " AND ".join([f"{col} = :where_{col}" for col in where_conditions.keys()])

    query = text(f"UPDATE {table_name} SET {set_clause} WHERE {where_clause}")

    params = {}

    for col, val in update_values.items():
        params[f"set_{col}"] = val

    for col, val in where_conditions.items():
        params[f"where_{col}"] = val

    with engine.begin() as connection:
        result = connection.execute(query, params)
        return result.rowcount


def delete_table_rows(table_name, where_conditions):
    engine = create_postgres_engine()

    where_clause = " AND ".join([f"{col} = :{col}" for col in where_conditions.keys()])
    query = text(f"DELETE FROM {table_name} WHERE {where_clause}")

    with engine.begin() as connection:
        result = connection.execute(query, where_conditions)
        return result.rowcount


def alter_table_add_column(table_name, column_name, data_type):
    engine = create_postgres_engine()
    query = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {data_type}"
    with engine.connect() as connection:
        result = connection.execute(query)


def alter_table_drop_column(table_name, column_name):
    engine = create_postgres_engine()
    query = f"ALTER TABLE {table_name} DROP COLUMN {column_name}"
    with engine.connect() as connection:
        result = connection.execute(query)
