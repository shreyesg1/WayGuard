"""NYC Open Data fetch utilities used by backend services."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Optional

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class DataFetcher:
    """Fetch and normalize 311, NYPD, and restaurant inspection datasets."""

    def __init__(self, config_path: str = "config.json") -> None:
        """Initialize API endpoints, auth token, and resilient HTTP session."""
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

        self.api_endpoints = self.config["api_endpoints"]
        self.app_token = os.environ.get("NYC_OPEN_DATA_TOKEN")

        self.session = requests.Session()
        retry_strategy = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[408, 429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _request_json_with_backoff(
        self,
        url: str,
        params: Optional[dict] = None,
        max_attempts: int = 5,
    ) -> Optional[list]:
        """Perform a GET with retry/backoff and return JSON list payload."""
        headers = {"X-App-Token": self.app_token} if self.app_token else {}
        for attempt in range(max_attempts):
            try:
                response = self.session.get(url, params=params, headers=headers, timeout=30)
                if response.status_code == 200:
                    payload = response.json()
                    return payload if payload else None
                if response.status_code in (408, 429, 500, 502, 503, 504):
                    time.sleep(min(8.0, 0.5 * (2**attempt)))
                    continue
                return None
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                time.sleep(min(8.0, 0.5 * (2**attempt)))
            except Exception:
                return None
        return None

    def _make_api_request(self, url: str, params: Optional[dict] = None) -> Optional[list]:
        """Proxy helper for API requests to simplify method callers."""
        return self._request_json_with_backoff(url, params=params)

    def fetch_311_data(
        self,
        days: int = 30,
        max_records: int = 20000,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """Fetch 311 incidents for the requested date window."""
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=days)
        start_dt = pd.to_datetime(start_date, errors="coerce")
        end_dt = pd.to_datetime(end_date, errors="coerce")
        if pd.isna(start_dt) or pd.isna(end_dt):
            start_dt = datetime.now() - timedelta(days=days)
            end_dt = datetime.now()

        all_data = []
        offset = 0
        batch_size = min(5000, int(max_records))
        while True:
            params = {
                "$where": (
                    f"created_date between '{start_dt.strftime('%Y-%m-%dT00:00:00')}' "
                    f"and '{end_dt.strftime('%Y-%m-%dT23:59:59')}'"
                ),
                "$select": "created_date,complaint_type,descriptor,latitude,longitude,incident_zip,borough",
                "$limit": batch_size,
                "$offset": offset,
                "$order": "created_date DESC",
            }
            data = self._make_api_request(self.api_endpoints["nyc_311"], params)
            if not data:
                break
            all_data.extend(data)
            if len(data) < batch_size or len(all_data) >= max_records:
                break
            offset += batch_size
            time.sleep(0.2)

        if not all_data:
            return pd.DataFrame()

        df = pd.DataFrame(all_data)
        if df.empty or "latitude" not in df.columns or "longitude" not in df.columns:
            return pd.DataFrame()
        df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
        df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
        df["created_date"] = pd.to_datetime(df["created_date"])
        return df.dropna(subset=["latitude", "longitude"]).head(max_records)

    def fetch_crime_data(self, days: int = 30, max_records: int = 15000) -> pd.DataFrame:
        """Fetch NYPD complaint records anchored to dataset max available date."""
        date_field = "cmplnt_fr_dt"
        max_date_payload = self._make_api_request(
            self.api_endpoints["nypd_complaints"],
            {"$select": f"max({date_field}) as max_date", "$limit": 1},
        )
        if max_date_payload and isinstance(max_date_payload, list) and max_date_payload[0].get("max_date"):
            end_date = pd.to_datetime(max_date_payload[0]["max_date"], errors="coerce")
        else:
            end_date = pd.Timestamp.now()
        if pd.isna(end_date):
            end_date = pd.Timestamp.now()
        start_date = end_date - timedelta(days=days)

        start_str = start_date.strftime("%Y-%m-%dT00:00:00.000")
        end_str = end_date.strftime("%Y-%m-%dT23:59:59.999")

        all_data = []
        offset = 0
        batch_size = 5000
        while True:
            params = {
                "$select": "cmplnt_fr_dt,ofns_desc,latitude,longitude,boro_nm",
                "$where": f"{date_field} >= '{start_str}' AND {date_field} <= '{end_str}'",
                "$limit": batch_size,
                "$offset": offset,
                "$order": f"{date_field} DESC",
            }
            batch_data = self._make_api_request(self.api_endpoints["nypd_complaints"], params)
            if not batch_data:
                break
            all_data.extend(batch_data)
            if len(batch_data) < batch_size or len(all_data) >= max_records:
                break
            offset += batch_size
            time.sleep(0.2)

        if not all_data:
            return pd.DataFrame()

        df = pd.DataFrame(all_data)
        df["cmplnt_fr_dt"] = pd.to_datetime(df["cmplnt_fr_dt"])
        df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
        df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
        df = df.dropna(subset=["latitude", "longitude"]).sort_values("cmplnt_fr_dt", ascending=False)
        return df.head(max_records)

    def fetch_health_data(
        self,
        days: int = 30,
        max_records: int = 10000,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """Fetch restaurant inspection violations for the requested date window."""
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=days)
        start_dt = pd.to_datetime(start_date, errors="coerce")
        end_dt = pd.to_datetime(end_date, errors="coerce")
        if pd.isna(start_dt) or pd.isna(end_dt):
            start_dt = datetime.now() - timedelta(days=days)
            end_dt = datetime.now()

        params = {
            "$where": (
                f"inspection_date between '{start_dt.strftime('%Y-%m-%d')}' "
                f"and '{end_dt.strftime('%Y-%m-%d')}'"
            ),
            "$select": "inspection_date,violation_code,violation_description,score,latitude,longitude,boro",
            "$limit": min(10000, int(max_records)),
            "$order": "inspection_date DESC",
        }
        data = self._make_api_request(self.api_endpoints["restaurant_inspections"], params)
        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data)
        if df.empty or "latitude" not in df.columns or "longitude" not in df.columns:
            return pd.DataFrame()
        df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
        df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
        df["inspection_date"] = pd.to_datetime(df["inspection_date"])
        df["score"] = pd.to_numeric(df["score"], errors="coerce")
        return df.dropna(subset=["latitude", "longitude"]).head(max_records)

    def get_all_data(self, days: int = 30) -> Dict[str, pd.DataFrame]:
        """Fetch all supported datasets in one call."""
        return {
            "complaints": self.fetch_311_data(days),
            "crime": self.fetch_crime_data(days),
            "health": self.fetch_health_data(days),
        }
