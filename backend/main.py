from functools import lru_cache

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from backend.schemas import (
    AnalyticsHotspotsResponse,
    AnalyticsOverviewResponse,
    AnalyticsSummaryResponse,
    ExplainRouteRequest,
    ExplainRouteResponse,
    AnalyticsTrendsResponse,
    GeocodeSuggestResponse,
    NavigationRequest,
    NavigationResponse,
)
from backend.services.analytics_service import AnalyticsService
from backend.services.navigation_service import NavigationService
from backend.services.route_explainer_service import RouteExplainerService

load_dotenv("backend/.env")


app = FastAPI(title="CityScope API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@lru_cache(maxsize=1)
def get_navigation_service() -> NavigationService:
    return NavigationService()


@lru_cache(maxsize=1)
def get_analytics_service() -> AnalyticsService:
    return AnalyticsService()


@lru_cache(maxsize=1)
def get_route_explainer_service() -> RouteExplainerService:
    return RouteExplainerService()


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/geocode/suggest", response_model=GeocodeSuggestResponse)
def geocode_suggest(q: str = Query(..., min_length=3, max_length=300)) -> dict:
    try:
        suggestions = get_navigation_service().suggest_locations(q)
        return {"query": q, "suggestions": suggestions}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Geocoding failed: {exc}") from exc


@app.post("/navigation/compute", response_model=NavigationResponse)
def navigation_compute(payload: NavigationRequest) -> dict:
    try:
        return get_navigation_service().compute_routes(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Route computation failed: {exc}") from exc


@app.post("/navigation/explain-route", response_model=ExplainRouteResponse)
def navigation_explain_route(payload: ExplainRouteRequest) -> dict:
    try:
        explanation = get_route_explainer_service().explain_route(payload.model_dump())
        return {"explanation": explanation}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Route explanation failed: {exc}") from exc


@app.get("/analytics/summary", response_model=AnalyticsSummaryResponse)
def analytics_summary(days: int = Query(default=30, ge=1, le=90)) -> dict:
    try:
        return get_analytics_service().summary(days=days)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Summary failed: {exc}") from exc


@app.get("/analytics/trends", response_model=AnalyticsTrendsResponse)
def analytics_trends(days: int = Query(default=30, ge=1, le=90)) -> dict:
    try:
        return get_analytics_service().trends(days=days)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Trends failed: {exc}") from exc


@app.get("/analytics/hotspots", response_model=AnalyticsHotspotsResponse)
def analytics_hotspots(days: int = Query(default=30, ge=1, le=90)) -> dict:
    try:
        return get_analytics_service().hotspots(days=days)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Hotspots failed: {exc}") from exc


@app.get("/analytics/overview", response_model=AnalyticsOverviewResponse)
def analytics_overview(days: int = Query(default=30, ge=1, le=90)) -> dict:
    try:
        return get_analytics_service().overview(days=days)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Overview failed: {exc}") from exc
