import os
from pathlib import Path

import pandas as pd
import snowflake.connector
from dotenv import load_dotenv
from snowflake.connector.pandas_tools import write_pandas


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

DATA_PATH = PROJECT_ROOT / "data" / "processed" / "clean_pm25_latest.csv"

df = pd.read_csv(DATA_PATH)

df.columns = [col.upper() for col in df.columns]

conn = snowflake.connector.connect(
    user=os.getenv("SNOWFLAKE_USER"),
    password=os.getenv("SNOWFLAKE_PASSWORD"),
    account=os.getenv("SNOWFLAKE_ACCOUNT"),
    warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
    database=os.getenv("SNOWFLAKE_DATABASE"),
    schema=os.getenv("SNOWFLAKE_SCHEMA")
)

cursor = conn.cursor()

cursor.execute("""
CREATE OR REPLACE TABLE PM25_LATEST (
    SENSOR_ID NUMBER,
    PM25_VALUE FLOAT,
    DATETIME_UTC TIMESTAMP_TZ,
    DATETIME_LOCAL TIMESTAMP_TZ,
    LATITUDE FLOAT,
    LONGITUDE FLOAT,
    PARAMETER_ID NUMBER,
    PARAMETER_NAME STRING,
    UNIT STRING,
    DATE DATE,
    HOUR NUMBER,
    DATA_LOADED_AT TIMESTAMP_TZ,
    PM25_CATEGORY STRING
);
""")

success, nchunks, nrows, _ = write_pandas(
    conn=conn,
    df=df,
    table_name="PM25_LATEST"
)

print("Upload success:", success)
print("Chunks uploaded:", nchunks)
print("Rows uploaded:", nrows)

cursor.close()
conn.close()