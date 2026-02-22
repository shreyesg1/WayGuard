from typing import List, Optional, Tuple, Dict
import requests


LatLon = Tuple[float, float]


def parse_latlon_input(raw: str) -> Optional[LatLon]:
    """Parse a 'lat, lon' string into validated coordinates."""
    if not raw:
        return None
    parts = [p.strip() for p in raw.split(",")]
    if len(parts) != 2:
        return None
    try:
        lat = float(parts[0])
        lon = float(parts[1])
    except ValueError:
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    return lat, lon


def geocode_address_nominatim(query: str) -> Optional[LatLon]:
    """Geocode a single address query with Nominatim."""
    if not query:
        return None
    url = "https://nominatim.openstreetmap.org/search"
    response = requests.get(
        url,
        params={"q": query, "format": "json", "limit": 1},
        headers={"User-Agent": "WayGuard/1.0"},
        timeout=15,
    )
    response.raise_for_status()
    items = response.json()
    if not items:
        return None
    return float(items[0]["lat"]), float(items[0]["lon"])


def geocode_suggestions_nominatim(query: str, limit: int = 5) -> List[Dict]:
    """Return Nominatim suggestions for autocomplete inputs."""
    if not query or len(query.strip()) < 3:
        return []
    url = "https://nominatim.openstreetmap.org/search"
    response = requests.get(
        url,
        params={
            "q": query,
            "format": "json",
            "addressdetails": 1,
            "limit": max(1, min(limit, 8)),
            "dedupe": 1,
        },
        headers={"User-Agent": "WayGuard/1.0"},
        timeout=15,
    )
    response.raise_for_status()
    items = response.json() or []
    suggestions: List[Dict] = []
    for item in items:
        try:
            lat = float(item["lat"])
            lon = float(item["lon"])
            display_name = item.get("display_name", f"{lat:.5f}, {lon:.5f}")
            suggestions.append(
                {
                    "display_name": display_name,
                    "lat": lat,
                    "lon": lon,
                }
            )
        except Exception:
            continue
    return suggestions
