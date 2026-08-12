import json
import sqlite3
import pandas as pd
from .config import RAW_DIR, SOURCE_DB

def extract_data():
    """
    Extract data from:
      - customers.csv
      - orders.csv
      - products.json
      - stores table in store.db
    Return a dictionary of DataFrames.
    """
    # 1. Read customers CSV
    customers = pd.read_csv(RAW_DIR / "customers.csv")
    
    # 2. Read orders CSV
    orders = pd.read_csv(RAW_DIR / "orders.csv")
    
    # 3. Read and flatten products JSON
    with open(RAW_DIR / "products.json", "r", encoding="utf-8") as f:
        products_raw = json.load(f)
    products = pd.json_normalize(products_raw)
    
    # 4. Read stores from SQLite database
    conn = sqlite3.connect(SOURCE_DB)
    stores = pd.read_sql_query("SELECT * FROM stores", conn)
    conn.close()

    return {
        "customers": customers,
        "orders": orders,
        "products": products,
        "stores": stores
    }