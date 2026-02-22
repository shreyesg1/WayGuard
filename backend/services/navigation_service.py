from __future__ import annotations

from typing import Dict, Tuple

import pandas as pd

from backend.schemas import NavigationRequest
from data.data_fetcher import DataFetcher
from models.route_scorer import score_routes
from models.risk_surface import RiskSurface
from routing.ors_client import OpenRouteServiceClient
from utils.geolocation import geocode_suggestions_nominatim
from utils.helpers import load_config


class NavigationService:
    def __init__(self) -> None:
        self.fetcher = DataFetcher()
        self.config = load_config()

    def suggest_locations(self, query: str) -> list[dict]:
        return geocode_suggestions_nominatim(query=query, limit=5)

    def _selected_weights(self, request: NavigationRequest) -> Dict[str, float]:
        return {
            "crime": request.w_crime if request.use_crime else 0.0,
            "complaints": request.w_complaints if request.use_complaints else 0.0,
            "health": request.w_health if request.use_health else 0.0,
        }

    def _fetch_route_data(self, request: NavigationRequest) -> Dict[str, pd.DataFrame]:
        datasets: Dict[str, pd.DataFrame] = {
            "crime": pd.DataFrame(),
            "complaints": pd.DataFrame(),
            "health": pd.DataFrame(),
        }
        if request.use_crime:
            datasets["crime"] = self.fetcher.fetch_crime_data(days=request.time_window_days, max_records=12000)
        if request.use_complaints:
            datasets["complaints"] = self.fetcher.fetch_311_data(days=request.time_window_days, max_records=12000)
        if request.use_health:
            datasets["health"] = self.fetcher.fetch_health_data(days=request.time_window_days, max_records=8000)
        return datasets

    @staticmethod
    def _to_latlon_tuple(point) -> Tuple[float, float]:
        return float(point.lat), float(point.lon)

    def compute_routes(self, request: NavigationRequest) -> dict:
        weights = self._selected_weights(request)
        if sum(weights.values()) <= 0:
            raise ValueError("At least one dataset weight must be greater than zero.")

        route_data = self._fetch_route_data(request)
        routing_client = OpenRouteServiceClient(api_key=request.ors_key_override)
        effective_alternatives = max(2, min(int(request.alternatives), 3))
        routes = routing_client.get_routes(
            start_latlon=self._to_latlon_tuple(request.origin),
            end_latlon=self._to_latlon_tuple(request.destination),
            mode=request.mode,
            alternatives=effective_alternatives,
        )

        risk_surface = RiskSurface.build_surface(
            dfs=route_data,
            config=self.config,
            time_window=request.time_window_days,
            mode=request.mode,
            weights=weights,
        )
        scored = score_routes(
            routes=routes,
            risk_surface=risk_surface,
            mode=request.mode,
            risk_aversion=request.risk_aversion,
            risk_aggregate="p95",
        )
        if scored.empty:
            raise RuntimeError("No routes returned by routing provider.")

        score_by_id = {row["route_id"]: row for _, row in scored.iterrows()}
        enriched_routes: list[dict] = []
        for route in routes:
            row = score_by_id.get(route.route_id)
            if row is None:
                continue
            enriched_routes.append(
                {
                    "route_id": route.route_id,
                    "geometry": [{"lat": lat, "lon": lon} for lat, lon in route.geometry],
                    "duration_s": float(route.duration_s),
                    "distance_m": float(route.distance_m),
                    "risk_sum": float(row["risk_sum"]),
                    "risk_p95": float(row["risk_p95"]),
                    "risk_max": float(row["risk_max"]),
                    "risk_metric_used": str(row.get("risk_metric_used", "risk_agg")),
                    "total_cost": float(row["total_cost"]),
                    "recommended": bool(row["recommended"]),
                }
            )

        metadata = {
            "mode": request.mode,
            "time_window_days": request.time_window_days,
            "risk_aversion": request.risk_aversion,
            "requested_alternatives": int(request.alternatives),
            "effective_alternatives": effective_alternatives,
            "weights": weights,
            "risk_surface_cells": len(risk_surface.hex_risk),
            "datasets_count": {
                "crime": int(len(route_data["crime"])),
                "complaints": int(len(route_data["complaints"])),
                "health": int(len(route_data["health"])),
            },
            "route_risk": {
                "sum_min": float(scored["risk_sum"].min()),
                "sum_max": float(scored["risk_sum"].max()),
                "p95_min": float(scored["risk_p95"].min()),
                "p95_max": float(scored["risk_p95"].max()),
                "max_min": float(scored["risk_max"].min()),
                "max_max": float(scored["risk_max"].max()),
                "metric_used": str(scored["risk_metric_used"].iloc[0]),
            },
        }
        return {
            "recommended_route_id": str(scored.iloc[0]["route_id"]),
            "origin": request.origin.model_dump(),
            "destination": request.destination.model_dump(),
            "routes": enriched_routes,
            "metadata": metadata,
        }
