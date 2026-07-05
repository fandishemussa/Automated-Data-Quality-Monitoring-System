"""Create sample source tables and seed valid/invalid records.

Run from the project root:
    python database/seed_sample_data.py

This script resets the sample `customers`, `orders`, and `products` tables so
the project can be demonstrated repeatedly with predictable data quality
issues.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_sources.postgres_connector import create_postgres_engine
from utils.logger import get_logger


logger = get_logger(__name__)


RESET_TABLE_SQL = [
    "DROP TABLE IF EXISTS orders",
    "DROP TABLE IF EXISTS products",
    "DROP TABLE IF EXISTS customers",
]

CREATE_TABLE_SQL = [
    """
    CREATE TABLE customers (
        customer_id INT PRIMARY KEY,
        name VARCHAR(100),
        email VARCHAR(100),
        created_at TIMESTAMP
    )
    """,
    """
    CREATE TABLE orders (
        order_id INT PRIMARY KEY,
        customer_id INT,
        order_date TIMESTAMP,
        amount NUMERIC(12, 2),
        status VARCHAR(50)
    )
    """,
    """
    CREATE TABLE products (
        product_id INT PRIMARY KEY,
        product_name VARCHAR(200),
        price NUMERIC(12, 2),
        stock INT,
        updated_at TIMESTAMP
    )
    """,
]


def _sample_rows() -> dict[str, list[dict[str, Any]]]:
    """Return deterministic sample data with known quality issues."""

    now = datetime.now()

    return {
        "customers": [
            {
                "customer_id": 1,
                "name": "Alice Walker",
                "email": "alice@gmail.com",
                "created_at": now,
            },
            {
                "customer_id": 2,
                "name": "Ben Carter",
                "email": None,
                "created_at": now,
            },
            {
                "customer_id": 3,
                "name": "Cy",
                "email": "not-an-email",
                "created_at": now - timedelta(days=10),
            },
            {
                "customer_id": 4,
                "name": "Dana Smith",
                "email": "duplicate@yahoo.com",
                "created_at": now,
            },
            {
                "customer_id": 5,
                "name": "Evan Stone",
                "email": "duplicate@yahoo.com",
                "created_at": now,
            },
        ],
        "orders": [
            {
                "order_id": 101,
                "customer_id": 1,
                "order_date": now,
                "amount": 125.50,
                "status": "delivered",
            },
            {
                "order_id": 102,
                "customer_id": 999,
                "order_date": now,
                "amount": 49.99,
                "status": "pending",
            },
            {
                "order_id": 103,
                "customer_id": 2,
                "order_date": now + timedelta(days=1),
                "amount": 19.99,
                "status": "shipped",
            },
            {
                "order_id": 104,
                "customer_id": 3,
                "order_date": now,
                "amount": -25.00,
                "status": "unknown_status",
            },
        ],
        "products": [
            {
                "product_id": 201,
                "product_name": "Laptop Pro",
                "price": 1200.00,
                "stock": 15,
                "updated_at": now,
            },
            {
                "product_id": 202,
                "product_name": "Mouse-USB",
                "price": 25.00,
                "stock": 5,
                "updated_at": now,
            },
            {
                "product_id": 203,
                "product_name": "Broken Product",
                "price": -50.00,
                "stock": 10,
                "updated_at": now,
            },
            {
                "product_id": 204,
                "product_name": "Old Keyboard",
                "price": 45.00,
                "stock": -2,
                "updated_at": now - timedelta(days=10),
            },
        ],
    }


def reset_sample_tables() -> None:
    """Drop and recreate the sample source tables."""

    engine = create_postgres_engine()

    with engine.begin() as connection:
        for statement in RESET_TABLE_SQL:
            connection.execute(text(statement))

        for statement in CREATE_TABLE_SQL:
            connection.execute(text(statement))

    logger.info("Sample source tables reset successfully.")


def seed_sample_data() -> None:
    """Insert sample rows into customers, orders, and products."""

    engine = create_postgres_engine()
    rows = _sample_rows()

    insert_statements = {
        "customers": text(
            """
            INSERT INTO customers (customer_id, name, email, created_at)
            VALUES (:customer_id, :name, :email, :created_at)
            """
        ),
        "orders": text(
            """
            INSERT INTO orders (order_id, customer_id, order_date, amount, status)
            VALUES (:order_id, :customer_id, :order_date, :amount, :status)
            """
        ),
        "products": text(
            """
            INSERT INTO products (product_id, product_name, price, stock, updated_at)
            VALUES (:product_id, :product_name, :price, :stock, :updated_at)
            """
        ),
    }

    with engine.begin() as connection:
        for table_name, table_rows in rows.items():
            connection.execute(insert_statements[table_name], table_rows)
            logger.info("Inserted %s sample row(s) into %s.", len(table_rows), table_name)


def main() -> None:
    """Reset and seed sample source data."""

    reset_sample_tables()
    seed_sample_data()
    logger.info("Sample data seeding completed.")


if __name__ == "__main__":
    main()
