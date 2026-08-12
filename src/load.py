import sqlite3
from .config import WAREHOUSE_DB

def load_data(customers, products, sales):
    WAREHOUSE_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(WAREHOUSE_DB)
    cursor = conn.cursor()

    # 1. Create Tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dim_customer (
            customer_id TEXT PRIMARY KEY,
            name TEXT,
            province TEXT,
            email TEXT
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dim_product (
            product_id TEXT PRIMARY KEY,
            product_name TEXT,
            category TEXT,
            price REAL
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fact_sales (
            order_id TEXT PRIMARY KEY,
            customer_id TEXT,
            product_id TEXT,
            order_date TEXT,
            qty INTEGER,
            unit_price REAL,
            discount_pct REAL,
            sales_amount REAL
        );
    """)

    # 2. Prepare & Insert Data
    cust_data = [
        (row["customer_id"], row["name"], row["province"], row["email"])
        for _, row in customers.iterrows()
    ]
    cursor.executemany("""
        INSERT OR REPLACE INTO dim_customer (customer_id, name, province, email)
        VALUES (?, ?, ?, ?)
    """, cust_data)

    prod_data = [
        (row["product_id"], row["product_name"], row["category"], row["price"])
        for _, row in products.iterrows()
    ]
    cursor.executemany("""
        INSERT OR REPLACE INTO dim_product (product_id, product_name, category, price)
        VALUES (?, ?, ?, ?)
    """, prod_data)

    sales_data = [
        (
            row["order_id"], row["customer_id"], row["product_id"],
            row["order_date"], int(row["qty"]), float(row["unit_price"]),
            float(row["discount_pct"]), float(row["sales_amount"])
        )
        for _, row in sales.iterrows()
    ]
    cursor.executemany("""
        INSERT OR REPLACE INTO fact_sales (
            order_id, customer_id, product_id, order_date,
            qty, unit_price, discount_pct, sales_amount
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, sales_data)

    conn.commit()
    conn.close()