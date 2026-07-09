import dotenv
import os
dotenv.load_dotenv(os.getenv("ENV_FILE", ".env"))

import pandas as pd
from sqlalchemy import create_engine
from src.app.config import settings

CSV_PATH = "data/raw/us_regional_sales.csv"

COLUMN_MAP = {
    "OrderNumber": "order_number",
    "Sales Channel": "sales_channel",
    "WarehouseCode": "warehouse_code",
    "ProcuredDate": "procured_date",
    "OrderDate": "order_date",
    "ShipDate": "ship_date",
    "DeliveryDate": "delivery_date",
    "CurrencyCode": "currency_code",
    "_SalesTeamID": "sales_team_id",
    "_CustomerID": "customer_id",
    "_StoreID": "store_id",
    "_ProductID": "product_id",
    "Order Quantity": "order_quantity",
    "Discount Applied": "discount_applied",
    "Unit Cost": "unit_cost",
    "Unit Price": "unit_price",
}

DATE_COLS = ["procured_date", "order_date", "ship_date", "delivery_date"]
MONEY_COLS = ["unit_cost", "unit_price"]


def main():
    df = pd.read_csv(CSV_PATH)
    df = df.rename(columns=COLUMN_MAP)
    df = df[list(COLUMN_MAP.values())]

    # Order numbers have stray spaces: "SO - 000101" -> normalize if you want
    # exact matching later; leaving as-is preserves the raw value.
    df["order_number"] = df["order_number"].str.strip()

    # Dates are DD-MM-YYYY, not ISO — dayfirst=True is required or pandas
    # will silently mis-parse anything where day <= 12.
    for col in DATE_COLS:
        df[col] = pd.to_datetime(df[col], dayfirst=True, errors="coerce")

    # Money columns have comma thousand-separators, so they load as strings
    # (e.g. "1,001.18") — strip commas before casting to float.
    for col in MONEY_COLS:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace(",", "", regex=False)
            .astype(float)
        )

    engine = create_engine(settings.sync_database_url)
    df.to_sql("sales", engine, if_exists="append", index=False)
    print(f"Inserted {len(df)} rows into sales.")


if __name__ == "__main__":
    main()