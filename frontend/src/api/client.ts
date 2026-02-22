import axios from "axios";
import type {
  AnalyticsHotspotsResponse,
    AnalyticsOverviewResponse,
  AnalyticsSummaryResponse,
  AnalyticsTrendsResponse,
  ExplainRoutePayload,
  ExplainRouteResponse,
  GeocodeSuggestion,
  NavigationComputePayload,
  NavigationResponse,
} from "../types";

const baseURL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

const api = axios.create({
  baseURL,
  timeout: 120000,
});

export async function fetchGeocodeSuggestions(query: string): Promise<GeocodeSuggestion[]> {
  if (!query || query.trim().length < 3) {
    return [];
  }
  const { data } = await api.get<{ query: string; suggestions: GeocodeSuggestion[] }>("/geocode/suggest", {
    params: { q: query.trim() },
  });
  return data.suggestions ?? [];
}

export async function computeNavigation(payload: NavigationComputePayload): Promise<NavigationResponse> {
  const { data } = await api.post<NavigationResponse>("/navigation/compute", payload);
  return data;
}

export async function explainRoute(payload: ExplainRoutePayload): Promise<ExplainRouteResponse> {
  const { data } = await api.post<ExplainRouteResponse>("/navigation/explain-route", payload);
  return data;
}

export async function fetchSummary(days: number): Promise<AnalyticsSummaryResponse> {
  const { data } = await api.get<AnalyticsSummaryResponse>("/analytics/summary", { params: { days } });
  return data;
}

export async function fetchTrends(days: number): Promise<AnalyticsTrendsResponse> {
  const { data } = await api.get<AnalyticsTrendsResponse>("/analytics/trends", { params: { days } });
  return data;
}

export async function fetchHotspots(days: number): Promise<AnalyticsHotspotsResponse> {
  const { data } = await api.get<AnalyticsHotspotsResponse>("/analytics/hotspots", { params: { days } });
  return data;
}

export async function fetchAnalyticsOverview(days: number): Promise<AnalyticsOverviewResponse> {
  const { data } = await api.get<AnalyticsOverviewResponse>("/analytics/overview", { params: { days } });
  return data;
}
