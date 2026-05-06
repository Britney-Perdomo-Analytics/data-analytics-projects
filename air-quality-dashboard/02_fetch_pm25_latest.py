import os
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv


# -----------------------------
# Setup
# -----------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

API_KEY = os.getenv("OPENAQ_API_KEY")

if not API_KEY:
    raise ValueError("OPENAQ_API_KEY is missing. Check your .env file.")

RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"

RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)


# -----------------------------
# Fetch latest PM2.5 data
# -----------------------------
url = "https://api.openaq.org/v3/parameters/2/latest"

headers = {
    "X-API-Key": API_KEY
}

params = {
    "limit": 1000,
    "page": 1
}

response = requests.get(url, headers=headers, params=params)

print("Status code:", response.status_code)

if response.status_code != 200:
    print(response.text)
    raise Exception("API request failed.")

data = response.json()
results = data.get("results", [])

print("Number of results:", len(results))

if len(results) == 0:
    raise Exception("No results returned from API.")


# -----------------------------
# Flatten API response
# -----------------------------
rows = []

for item in results:
    coordinates = item.get("coordinates") or {}
    datetime_obj = item.get("datetime") or {}

    rows.append({
        "sensor_id": item.get("sensorsId"),
        "pm25_value": item.get("value"),
        "datetime_utc": datetime_obj.get("utc"),
        "datetime_local": datetime_obj.get("local"),
        "latitude": coordinates.get("latitude"),
        "longitude": coordinates.get("longitude"),
        "parameter_id": 2,
        "parameter_name": "pm25",
        "unit": "µg/m³"
    })

raw_df = pd.DataFrame(rows)

raw_output_path = RAW_DATA_DIR / "raw_pm25_latest.csv"
raw_df.to_csv(raw_output_path, index=False)

print(f"Saved raw file: {raw_output_path}")
print("Raw preview:")
print(raw_df.head())


# -----------------------------
# Clean PM2.5 data
# -----------------------------
clean_df = raw_df.copy()

clean_df = clean_df.dropna(subset=[
    "sensor_id",
    "pm25_value",
    "latitude",
    "longitude"
])

clean_df["pm25_value"] = pd.to_numeric(clean_df["pm25_value"], errors="coerce")
clean_df["datetime_utc"] = pd.to_datetime(clean_df["datetime_utc"], errors="coerce", utc=True)
#clean_df["datetime_local"] = pd.to_datetime(clean_df["datetime_local"], errors="coerce")
clean_df["datetime_local"] = pd.to_datetime(clean_df["datetime_local"], errors="coerce", utc=True)


cutoff_date = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=30)
clean_df = clean_df[clean_df["datetime_utc"] >= cutoff_date]


clean_df = clean_df.dropna(subset=["pm25_value"])

clean_df = clean_df[
    (clean_df["pm25_value"] >= 0) &
    (clean_df["pm25_value"] <= 1000)
]

# -----------------------------
# Add location data from Day 1
# -----------------------------
# Location matching note
# -----------------------------
# Day 1 pulled location metadata, but the PM2.5 latest endpoint gives sensor-level data.
# The Day 1 location_id and the Day 2 sensor_id are not the same key.
# I tested matching by rounded latitude/longitude, but only a few rows matched.
# Because coordinate matching is unreliable, this script keeps latitude/longitude only.
# Later, location names/cities should be added by pulling sensor/location metadata
# and joining on the correct sensor-to-location relationship.
# -----------------------------

# locations_path = RAW_DATA_DIR / "raw_air_quality_locations.csv"

# if locations_path.exists():
#     locations_df = pd.read_csv(locations_path)

#     locations_df = locations_df.rename(columns={
#         "latitude": "location_latitude",
#         "longitude": "location_longitude"
#     })

#     # Round coordinates so they are easier to match
#     clean_df["lat_round"] = clean_df["latitude"].round(3)
#     clean_df["lon_round"] = clean_df["longitude"].round(3)

#     locations_df["lat_round"] = locations_df["location_latitude"].round(3)
#     locations_df["lon_round"] = locations_df["location_longitude"].round(3)

#     location_cols = [
#         "location_id",
#         "location_name",
#         "locality",
#         "country_name",
#         "timezone",
#         "provider_name",
#         "lat_round",
#         "lon_round"
#     ]

#     available_cols = [col for col in location_cols if col in locations_df.columns]

#     clean_df = clean_df.merge(
#         locations_df[available_cols],
#         on=["lat_round", "lon_round"],
#         how="left"
#     )

#     clean_df = clean_df.drop(columns=["lat_round", "lon_round"])

# else:
#     print("Warning: raw_air_quality_locations.csv not found. Location names were not added.")


# -----------------------------
# Add dashboard fields
# -----------------------------
clean_df["date"] = clean_df["datetime_utc"].dt.date
clean_df["hour"] = clean_df["datetime_utc"].dt.hour
clean_df["data_loaded_at"] = pd.Timestamp.now(tz="UTC")


def categorize_pm25(value):
    if value <= 12:
        return "Good"
    elif value <= 35.4:
        return "Moderate"
    elif value <= 55.4:
        return "Unhealthy for Sensitive Groups"
    elif value <= 150.4:
        return "Unhealthy"
    elif value <= 250.4:
        return "Very Unhealthy"
    else:
        return "Hazardous"


clean_df["pm25_category"] = clean_df["pm25_value"].apply(categorize_pm25)


# -----------------------------
# Final sorting and saving
# -----------------------------
clean_df = clean_df.sort_values(by="pm25_value", ascending=False)

clean_output_path = PROCESSED_DATA_DIR / "clean_pm25_latest.csv"
clean_df.to_csv(clean_output_path, index=False)

print(f"Saved clean file: {clean_output_path}")
print("Clean preview:")
print(clean_df.head(10))
print("Rows in clean data:", len(clean_df))
#print("Rows with matched location names:", clean_df["location_name"].notna().sum() if "location_name" in clean_df.columns else 0)