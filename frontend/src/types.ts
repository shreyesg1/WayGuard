export type TravelMode = "walking" | "driving";

export interface LatLon {
  lat: number;
  lon: number;
}

export interface GeocodeSuggestion {
  display_name: string;
  lat: number;
  lon: number;
}

export interface RoutePoint {
  lat: number;
  lon: number;
}

export interface NavigationRoute {
  route_id: string;
  geometry: RoutePoint[];
  duration_s: number;
  distance_m: number;
  risk_sum: number;
  risk_p95: number;
  risk_max: number;
  risk_metric_used?: string;
  total_cost: number;
  recommended: boolean;
}

export interface NavigationComputePayload {
  origin: LatLon;
  destination: LatLon;
  mode: TravelMode;
  alternatives: number;
  time_window_days: number;
  risk_aversion: number;
  use_crime: boolean;
  use_complaints: boolean;
  use_health: boolean;
  w_crime: number;
  w_complaints: number;
  w_health: number;
}

export interface NavigationResponse {
  recommended_route_id: string;
  origin: LatLon;
  destination: LatLon;
  routes: NavigationRoute[];
  metadata: Record<string, unknown>;
}

export interface ExplainRoutePayload {
  route: NavigationRoute;
  context: {
    mode?: TravelMode;
    risk_aversion?: number;
  };
}

export interface ExplainRouteResponse {
  explanation: string;
}

export interface AnalyticsSummaryResponse {
  days: number;
  summary: Record<string, { total_incidents: number; areas_affected: number; average_risk_score: number | null }>;
  totals: { incidents: number };
}

export interface TrendPoint {
  date: string;
  count: number;
}

export interface AnalyticsTrendsResponse {
  days: number;
  trends: Record<string, TrendPoint[]>;
}

export interface AnalyticsHotspotsResponse {
  days: number;
  hotspots: Array<{
    center_lat: number;
    center_lon: number;
    count: number;
    density: number;
    area_km2: number;
  }>;
}

export interface AnalyticsOverviewResponse {
  days: number;
  summary: Record<string, { total_incidents: number; areas_affected: number; average_risk_score: number | null }>;
  totals: { incidents: number };
  trends: Record<string, TrendPoint[]>;
  hotspots: Array<{
    center_lat: number;
    center_lon: number;
    count: number;
    density: number;
    area_km2: number;
  }>;
  freshness: Record<string, { min_date: string | null; max_date: string | null }>;
  heat_points: Array<{ lat: number; lon: number; intensity: number }>;
}
