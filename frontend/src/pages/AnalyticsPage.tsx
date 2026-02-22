import { useEffect, useState } from "react";
import { CircleMarker, MapContainer, TileLayer, Tooltip } from "react-leaflet";
import { fetchAnalyticsOverview } from "../api/client";
import AnalyticsCharts from "../components/AnalyticsCharts";
import HeatLayer from "../components/HeatLayer";
import type {
  AnalyticsHotspotsResponse,
  AnalyticsOverviewResponse,
  AnalyticsSummaryResponse,
  AnalyticsTrendsResponse,
} from "../types";

export default function AnalyticsPage() {
  const [days, setDays] = useState(30);
  const [summary, setSummary] = useState<AnalyticsSummaryResponse | null>(null);
  const [trends, setTrends] = useState<AnalyticsTrendsResponse | null>(null);
  const [hotspots, setHotspots] = useState<AnalyticsHotspotsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [heatPoints, setHeatPoints] = useState<Array<{ lat: number; lon: number; intensity: number }>>([]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchAnalyticsOverview(days)
      .then((overview: AnalyticsOverviewResponse) => {
        if (cancelled) return;
        setSummary({ days: overview.days, summary: overview.summary, totals: overview.totals });
        setTrends({ days: overview.days, trends: overview.trends });
        setHotspots({ days: overview.days, hotspots: overview.hotspots });
        setHeatPoints(overview.heat_points ?? []);
      })
      .catch((err: any) => {
        if (cancelled) return;
        setError(err?.response?.data?.detail ?? "Failed to load analytics.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [days]);

  return (
    <div className="page-layout">
      <section className="card">
        <div className="toolbar">
          <h2>Analytics</h2>
          <select value={days} onChange={(e) => setDays(Number(e.target.value))} aria-label="Analytics range">
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </select>
        </div>
        {loading && (
          <>
            <div className="loading-bar" aria-label="Loading analytics">
              <div className="loading-bar-inner" />
            </div>
            <p className="muted">Loading analytics...</p>
          </>
        )}
        {error && <p className="error-text">{error}</p>}
        {summary && (
          <div className="stats-grid">
            <div className="stat-card">
              <span>Total incidents</span>
              <strong>{summary.totals.incidents.toLocaleString()}</strong>
            </div>
            <div className="stat-card">
              <span>311 incidents</span>
              <strong>{summary.summary.complaints?.total_incidents?.toLocaleString() ?? "0"}</strong>
            </div>
            <div className="stat-card">
              <span>NYPD incidents</span>
              <strong>{summary.summary.crime?.total_incidents?.toLocaleString() ?? "0"}</strong>
            </div>
            <div className="stat-card">
              <span>Health incidents</span>
              <strong>{summary.summary.health?.total_incidents?.toLocaleString() ?? "0"}</strong>
            </div>
          </div>
        )}
      </section>

      <AnalyticsCharts trends={trends ?? undefined} />

      <section className="card">
        <h3>Hotspots</h3>
        <div className="map-shell">
          <MapContainer center={[40.7128, -74.006]} zoom={11} className="map-container">
            <TileLayer
              url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
              attribution='&copy; OpenStreetMap contributors &copy; CARTO'
            />
            <HeatLayer
              points={heatPoints}
            />
            {(hotspots?.hotspots ?? []).map((h, idx) => (
              <CircleMarker
                key={`${h.center_lat}-${h.center_lon}-${idx}`}
                center={[h.center_lat, h.center_lon]}
                radius={Math.max(6, Math.min(18, (h.count ?? 1) / 10))}
                pathOptions={{ color: "#b30000", fillOpacity: 0.6 }}
              >
                <Tooltip>
                  Incidents: {Number(h.count ?? 0).toLocaleString()} | Density: {Number(h.density ?? 0).toFixed(1)}
                </Tooltip>
              </CircleMarker>
            ))}
          </MapContainer>
        </div>
      </section>
    </div>
  );
}
