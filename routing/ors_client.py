"""Routing client abstractions and OpenRouteService integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import os

import requests


LatLon = Tuple[float, float]


@dataclass
class RouteOption:
    """Normalized route option returned by routing providers."""

    route_id: str
    geometry: List[LatLon]
    duration_s: float
    distance_m: float
    metadata: Dict


class RoutingClient:
    """Routing client interface."""

    def get_routes(
        self,
        start_latlon: LatLon,
        end_latlon: LatLon,
        mode: str = "walking",
        alternatives: int = 3,
    ) -> List[RouteOption]:
        """Return candidate routes between origin and destination."""
        raise NotImplementedError


class OpenRouteServiceClient(RoutingClient):
    """OpenRouteService implementation of the routing client interface."""

    BASE_URL = "https://api.openrouteservice.org/v2/directions"
    PROFILE_MAP = {
        "walking": "foot-walking",
        "driving": "driving-car",
    }

    def __init__(self, api_key: Optional[str] = None):
        """Resolve ORS API key from explicit argument or environment."""
        self.api_key = (
            api_key
            or os.environ.get("OPENROUTESERVICE_API_KEY")
            or os.environ.get("ORS_API_KEY")
        )
        if isinstance(self.api_key, str):
            self.api_key = self.api_key.strip()
        if not self.api_key:
            raise ValueError("Missing OpenRouteService API key. Set OPENROUTESERVICE_API_KEY.")

    def get_routes(
        self,
        start_latlon: LatLon,
        end_latlon: LatLon,
        mode: str = "walking",
        alternatives: int = 3,
    ) -> List[RouteOption]:
        """Fetch route alternatives from OpenRouteService and normalize output."""
        if mode not in self.PROFILE_MAP:
            raise ValueError(f"Unsupported mode '{mode}'. Use one of: {list(self.PROFILE_MAP.keys())}.")

        profile = self.PROFILE_MAP[mode]
        url = f"{self.BASE_URL}/{profile}/geojson"
        start_lat, start_lon = start_latlon
        end_lat, end_lon = end_latlon
        payload = {
            "coordinates": [[float(start_lon), float(start_lat)], [float(end_lon), float(end_lat)]],
            "alternative_routes": {
                "target_count": max(1, min(int(alternatives), 5)),
                "weight_factor": 1.5,
                "share_factor": 0.6,
            },
            "instructions": False,
        }

        response = requests.post(
            url,
            json=payload,
            headers={"Authorization": self.api_key},
            timeout=25,
        )
        response.raise_for_status()

        data = response.json()
        routes: List[RouteOption] = []
        for idx, feature in enumerate(data.get("features", [])):
            summary = feature.get("properties", {}).get("summary", {})
            coordinates = feature.get("geometry", {}).get("coordinates", [])
            geometry = [(float(c[1]), float(c[0])) for c in coordinates if len(c) >= 2]
            routes.append(
                RouteOption(
                    route_id=f"route_{idx + 1}",
                    geometry=geometry,
                    duration_s=float(summary.get("duration", 0.0)),
                    distance_m=float(summary.get("distance", 0.0)),
                    metadata=feature.get("properties", {}),
                )
            )

        if not routes:
            raise RuntimeError("Routing provider returned no routes.")
        return routes
