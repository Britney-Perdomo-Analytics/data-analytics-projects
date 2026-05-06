print("Script started")
import os
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENAQ_API_KEY")

if not API_KEY:
    raise ValueError("OPENAQ_API_KEY is missing. Check your .env file.")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

url = "https://api.openaq.org/v3/locations"

headers = {
    "X-API-Key": API_KEY
}

params = {
    "limit": 100,
    "page": 1
}

response = requests.get(url, headers=headers, params=params)

print("Status code:", response.status_code)

if response.status_code != 200:
    print(response.text)
    raise Exception("API request failed.")

data = response.json()
results = data.get("results", [])

rows = []

for item in results:
    coordinates = item.get("coordinates") or {}
    country = item.get("country") or {}
    owner = item.get("owner") or {}
    provider = item.get("provider") or {}

    rows.append({
        "location_id": item.get("id"),
        "location_name": item.get("name"),
        "locality": item.get("locality"),
        "timezone": item.get("timezone"),
        "latitude": coordinates.get("latitude"),
        "longitude": coordinates.get("longitude"),
        "country_id": country.get("id"),
        "country_name": country.get("name"),
        "owner_name": owner.get("name"),
        "provider_name": provider.get("name")
    })

df = pd.DataFrame(rows)

output_path = RAW_DATA_DIR / "raw_air_quality_locations.csv"
df.to_csv(output_path, index=False)

print(f"Saved {len(df)} rows to {output_path}")
print(df.head())