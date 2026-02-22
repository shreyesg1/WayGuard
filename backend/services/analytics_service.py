from __future__ import annotations

from functools import lru_cache
from typing import Dict

import pandas as pd

from data.data_fetcher import DataFetcher
from models.risk_scorer import RiskScorer
from utils.helpers import generate_summary_statistics


class AnalyticsService:
    def __init__(self) -> None:
        self.fetcher = DataFetcher()
        self.risk_scorer = RiskScorer()

    def fetch_all(self, days: int) -> Dict[str, pd.DataFrame]:
        crime_df = self.fetcher.fetch_crime_data(days=days, max_records=40000)
        data = {
            "crime": crime_df,
            "complaints": pd.DataFrame(),
            "health": pd.DataFrame(),
        }
        # Fetch 311/health directly in NYPD date window so series remain comparable
        # without clipping current-date slices down to empty frames.
        if crime_df is None or crime_df.empty or "cmplnt_fr_dt" not in crime_df.columns:
            return data

        crime_dates = pd.to_datetime(crime_df["cmplnt_fr_dt"], errors="coerce").dropna()
        if crime_dates.empty:
            return data

        window_start = crime_dates.min()
        window_end = crime_dates.max()
        data["complaints"] = self.fetcher.fetch_311_data(
            days=days,
            max_records=60000,
            start_date=window_start,
            end_date=window_end,
        )
        data["health"] = self.fetcher.fetch_health_data(
            days=days,
            max_records=20000,
            start_date=window_start,
            end_date=window_end,
        )
        return data

    @lru_cache(maxsize=8)
    def fetch_all_cached(self, days: int) -> Dict[str, pd.DataFrame]:
        return self.fetch_all(days=days)

    def summary(self, days: int) -> dict:
        data = self.fetch_all_cached(days=days)
        summary = {}
        total_incidents = 0
        for key, df in data.items():
            stats = generate_summary_statistics(df)
            summary[key] = stats
            total_incidents += int(stats["total_incidents"])
        return {
            "days": days,
            "summary": summary,
            "totals": {"incidents": total_incidents},
        }

    @staticmethod
    def _daily_trend(df: pd.DataFrame, date_col: str) -> list[dict]:
        if df is None or df.empty or date_col not in df.columns:
            return []
        local = df.copy()
        local[date_col] = pd.to_datetime(local[date_col], errors="coerce")
        local = local.dropna(subset=[date_col])
        if local.empty:
            return []
        grouped = (
            local.groupby(local[date_col].dt.date)
            .size()
            .reset_index(name="count")
            .rename(columns={date_col: "date"})
        )
        grouped["date"] = grouped["date"].astype(str)
        return grouped.to_dict(orient="records")

    def trends(self, days: int) -> dict:
        data = self.fetch_all_cached(days=days)
        trends = {
            "complaints": self._daily_trend(data["complaints"], "created_date"),
            "crime": self._daily_trend(data["crime"], "cmplnt_fr_dt"),
            "health": self._daily_trend(data["health"], "inspection_date"),
        }
        return {
            "days": days,
            "trends": trends,
        }

    def hotspots(self, days: int) -> dict:
        data = self.fetch_all_cached(days=days)
        frames = []
        for df in data.values():
            if df is None or df.empty:
                continue
            coords = df[["latitude", "longitude"]].dropna()
            if not coords.empty:
                frames.append(coords)
        if not frames:
            return {"days": days, "hotspots": []}

        all_coords = pd.concat(frames, ignore_index=True)
        hotspots = self.risk_scorer.detect_hotspots(all_coords)
        if hotspots is None or hotspots.empty:
            return {"days": days, "hotspots": []}

        cleaned = hotspots.copy()
        for col in ["center_lat", "center_lon", "count", "density", "area_km2"]:
            cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce")
        cleaned = cleaned.dropna(subset=["center_lat", "center_lon"])
        return {"days": days, "hotspots": cleaned.to_dict(orient="records")}

    def overview(self, days: int) -> dict:
        data = self.fetch_all_cached(days=days)
        summary = self.summary(days)
        trends = self.trends(days)
        hotspots = self.hotspots(days)
        heat_points = self._build_heat_points(data)
        freshness = {}
        date_map = {
            "complaints": "created_date",
            "crime": "cmplnt_fr_dt",
            "health": "inspection_date",
        }
        for key, date_col in date_map.items():
            df = data.get(key)
            if df is None or df.empty or date_col not in df.columns:
                freshness[key] = {"min_date": None, "max_date": None}
                continue
            local = pd.to_datetime(df[date_col], errors="coerce").dropna()
            if local.empty:
                freshness[key] = {"min_date": None, "max_date": None}
                continue
            freshness[key] = {
                "min_date": str(local.min().date()),
                "max_date": str(local.max().date()),
            }

        return {
            "days": days,
            "summary": summary["summary"],
            "totals": summary["totals"],
            "trends": trends["trends"],
            "hotspots": hotspots["hotspots"],
            "freshness": freshness,
            "heat_points": heat_points,
        }

    @staticmethod
    def _build_heat_points(data: Dict[str, pd.DataFrame], max_points: int = 20000) -> list[dict]:
        frames = []
        for df in data.values():
            if df is None or df.empty:
                continue
            if "latitude" not in df.columns or "longitude" not in df.columns:
                continue
            local = df[["latitude", "longitude"]].copy()
            local["latitude"] = pd.to_numeric(local["latitude"], errors="coerce")
            local["longitude"] = pd.to_numeric(local["longitude"], errors="coerce")
            local = local.dropna(subset=["latitude", "longitude"])
            local = local[
                (local["latitude"].between(40.4, 40.95)) &
                (local["longitude"].between(-74.25, -73.7))
            ]
            if not local.empty:
                frames.append(local)

        if not frames:
            return []

        merged = pd.concat(frames, ignore_index=True)
        if len(merged) > max_points:
            merged = merged.sample(n=max_points, random_state=42)

        return [
            {"lat": float(row.latitude), "lon": float(row.longitude), "intensity": 1.0}
            for row in merged.itertuples(index=False)
        ]
