import sqlite3
from .config import WAREHOUSE_DB

def validate_data(source_sales):
    """
    Validates pipeline consistency between Transformed Data and Warehouse DB.
    """
    conn = sqlite3.connect(WAREHOUSE_DB)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM fact_sales")
    warehouse_rows = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(order_id) - COUNT(DISTINCT order_id) FROM fact_sales")
    duplicate_order_ids = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(sales_amount) FROM fact_sales")
    wh_sum = cursor.fetchone()[0]
    warehouse_total_sales = float(wh_sum) if wh_sum is not None else 0.0

    conn.close()

    source_valid_rows = len(source_sales)
    source_total_sales = float(source_sales["sales_amount"].sum())

    source_total_sales_rounded = round(source_total_sales, 2)
    warehouse_total_sales_rounded = round(warehouse_total_sales, 2)

    is_pass = (
        source_valid_rows == warehouse_rows and
        duplicate_order_ids == 0 and
        abs(source_total_sales_rounded - warehouse_total_sales_rounded) < 0.01
    )

    return {
        "source_valid_rows": source_valid_rows,
        "warehouse_rows": warehouse_rows,
        "duplicate_order_ids": duplicate_order_ids,
        "source_total_sales": source_total_sales_rounded,
        "warehouse_total_sales": warehouse_total_sales_rounded,
        "status": "PASS" if is_pass else "FAIL"
    }