from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field


TravelMode = Literal["walking", "driving"]


class LatLon(BaseModel):
    lat: float
    lon: float


class NavigationRequest(BaseModel):
    origin: LatLon
    destination: LatLon
    mode: TravelMode = "walking"
    alternatives: int = Field(default=3, ge=2, le=5)
    time_window_days: int = Field(default=30, ge=7, le=90)
    risk_aversion: float = Field(default=0.5, ge=0.0, le=1.0)
    use_crime: bool = True
    use_complaints: bool = False
    use_health: bool = False
    w_crime: float = Field(default=1.0, ge=0.0, le=1.0)
    w_complaints: float = Field(default=0.4, ge=0.0, le=1.0)
    w_health: float = Field(default=0.3, ge=0.0, le=1.0)
    show_heat_overlay: bool = True
    ors_key_override: Optional[str] = None


class RoutePoint(BaseModel):
    lat: float
    lon: float


class NavigationRoute(BaseModel):
    route_id: str
    geometry: List[RoutePoint]
    duration_s: float
    distance_m: float
    risk_sum: float
    risk_p95: float
    risk_max: float
    total_cost: float
    recommended: bool


class NavigationResponse(BaseModel):
    recommended_route_id: str
    origin: LatLon
    destination: LatLon
    routes: List[NavigationRoute]
    metadata: Dict


class GeocodeSuggestion(BaseModel):
    display_name: str
    lat: float
    lon: float


class GeocodeSuggestResponse(BaseModel):
    query: str
    suggestions: List[GeocodeSuggestion]


class AnalyticsSummaryResponse(BaseModel):
    days: int
    summary: Dict
    totals: Dict


class AnalyticsTrendsResponse(BaseModel):
    days: int
    trends: Dict


class AnalyticsHotspotsResponse(BaseModel):
    days: int
    hotspots: List[Dict]


class AnalyticsOverviewResponse(BaseModel):
    days: int
    summary: Dict
    totals: Dict
    trends: Dict
    hotspots: List[Dict]
    freshness: Dict
    heat_points: List[Dict]


class ExplainRouteRequest(BaseModel):
    route: Dict
    context: Dict = Field(default_factory=dict)


class ExplainRouteResponse(BaseModel):
    explanation: str
