import pandas as pd
from .config import PROVINCE_MAP

def transform_data(raw):
    customers = raw["customers"].copy()
    products = raw["products"].copy()
    orders = raw["orders"].copy()

    # -------------------------------------------------------------
    # 1. Customers Cleaning
    # -------------------------------------------------------------
    customers = customers.drop_duplicates(subset=["customer_id"]).copy()

    def clean_province(p):
        if pd.isna(p):
            return "Unknown"
        p_str = str(p).strip().lower()
        return PROVINCE_MAP.get(p_str, str(p).strip().title())

    customers["province"] = customers["province"].apply(clean_province)
    customers["email"] = customers["email"].fillna("Unknown")
    customers["name"] = customers["name"].fillna("Unknown")

    clean_customers = customers[["customer_id", "name", "province", "email"]].copy()

    # -------------------------------------------------------------
    # 2. Products Cleaning
    # -------------------------------------------------------------
    products.columns = [col.replace(".", "_") for col in products.columns]

    rename_map = {}
    for col in products.columns:
        c_lower = col.lower()
        if "product_id" in c_lower or col == "id":
            rename_map[col] = "product_id"
        elif "name" in c_lower or "title" in c_lower:
            rename_map[col] = "product_name"
        elif "category" in c_lower or "cat" in c_lower:
            rename_map[col] = "category"
        elif "price" in c_lower:
            rename_map[col] = "price"

    products = products.rename(columns=rename_map)
    # ลบคอลัมน์ที่มีชื่อซ้ำกันออก ให้เหลือเพียงคอลัมน์แรก
    products = products.loc[:, ~products.columns.duplicated(keep="first")].copy()

    products = products.drop_duplicates(subset=["product_id"]).copy()

    # จัดการคอลัมน์ category
    if "category" not in products.columns:
        products["category"] = "Unknown"
    else:
        products["category"] = products["category"].fillna("Unknown")

    # จัดการคอลัมน์ price
    if "price" in products.columns:
        products["price"] = pd.to_numeric(products["price"], errors="coerce").fillna(0.0)
    else:
        products["price"] = 0.0

    if "product_name" not in products.columns:
        products["product_name"] = "Unknown"

    clean_products = products[["product_id", "product_name", "category", "price"]].copy()

    # -------------------------------------------------------------
    # 3. Orders Validation & Rejects Handling
    # -------------------------------------------------------------
    rejects_list = []

    # Check Duplicate order_id
    dup_mask = orders.duplicated(subset=["order_id"], keep="first")
    if dup_mask.any():
        rej_dup = orders[dup_mask].copy()
        rej_dup["reject_reason"] = "Duplicate order_id"
        rejects_list.append(rej_dup)
    orders = orders[~dup_mask].copy()

    # Parse date and normalize status
    orders["order_date_parsed"] = pd.to_datetime(orders["order_date"], errors="coerce")
    orders["status_norm"] = orders["status"].astype(str).str.strip().str.lower()

    # Validation Rules
    invalid_date = orders["order_date_parsed"].isna()
    invalid_qty = orders["qty"] <= 0
    invalid_price = orders["unit_price"] <= 0
    invalid_discount = (orders["discount_pct"] < 0) | (orders["discount_pct"] > 100)

    invalid_mask = invalid_date | invalid_qty | invalid_price | invalid_discount

    if invalid_mask.any():
        rej_rules = orders[invalid_mask].copy()
        reasons = []
        for _, row in rej_rules.iterrows():
            r = []
            if pd.isna(row["order_date_parsed"]): r.append("Invalid order date")
            if row["qty"] <= 0: r.append("qty <= 0")
            if row["unit_price"] <= 0: r.append("unit_price <= 0")
            if row["discount_pct"] < 0 or row["discount_pct"] > 100: r.append("discount_pct out of bounds")
            reasons.append("; ".join(r))
        rej_rules["reject_reason"] = reasons
        rejects_list.append(rej_rules)

    valid_orders = orders[~invalid_mask].copy()

    # Status Filtering (Paid / Completed)
    status_mask = valid_orders["status_norm"].isin(["paid", "completed"])
    if (~status_mask).any():
        rej_status = valid_orders[~status_mask].copy()
        rej_status["reject_reason"] = "Status not paid or completed"
        rejects_list.append(rej_status)

    valid_orders = valid_orders[status_mask].copy()

    # Master Foreign Key Matching
    cust_ids = set(clean_customers["customer_id"])
    prod_ids = set(clean_products["product_id"])

    missing_cust = ~valid_orders["customer_id"].isin(cust_ids)
    missing_prod = ~valid_orders["product_id"].isin(prod_ids)
    missing_fk_mask = missing_cust | missing_prod

    if missing_fk_mask.any():
        rej_fk = valid_orders[missing_fk_mask].copy()
        fk_reasons = []
        for _, row in rej_fk.iterrows():
            r = []
            if row["customer_id"] not in cust_ids: r.append("customer_id not found in master")
            if row["product_id"] not in prod_ids: r.append("product_id not found in master")
            fk_reasons.append("; ".join(r))
        rej_fk["reject_reason"] = fk_reasons
        rejects_list.append(rej_fk)

    final_orders = valid_orders[~missing_fk_mask].copy()

    # -------------------------------------------------------------
    # 4. Financial Calculations
    # -------------------------------------------------------------
    final_orders["order_date"] = final_orders["order_date_parsed"].dt.strftime("%Y-%m-%d")
    final_orders["gross_amount"] = final_orders["qty"] * final_orders["unit_price"]
    final_orders["discount_amount"] = final_orders["gross_amount"] * (final_orders["discount_pct"] / 100.0)
    final_orders["sales_amount"] = final_orders["gross_amount"] - final_orders["discount_amount"]

    sales = final_orders[[
        "order_id", "customer_id", "product_id", "order_date",
        "qty", "unit_price", "discount_pct", "sales_amount"
    ]].copy()

    # Combine Rejects
    if rejects_list:
        rejects = pd.concat(rejects_list, ignore_index=True)
        cols_to_drop = [c for c in ["order_date_parsed", "status_norm"] if c in rejects.columns]
        if cols_to_drop:
            rejects = rejects.drop(columns=cols_to_drop)
    else:
        rejects = pd.DataFrame()

    return clean_customers, clean_products, sales, rejects