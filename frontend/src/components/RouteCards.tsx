import { useState } from "react";
import { explainRoute } from "../api/client";
import type { NavigationRoute, TravelMode } from "../types";
import Button from "./ui/Button";

interface Props {
  routes: NavigationRoute[];
  mode?: TravelMode;
  riskAversion?: number;
}

function etaText(seconds: number): string {
  const mins = Math.round(seconds / 60);
  if (mins < 60) return `${mins} min`;
  return `${Math.floor(mins / 60)}h ${mins % 60}m`;
}

function InfoMetric({
  label,
  value,
  help,
}: {
  label: string;
  value: string;
  help: string;
}) {
  return (
    <span className="metric-with-help" title={help}>
      <span className="metric-label">
        {label}
        <span className="info-dot" aria-label={`${label} info`}>
          i
        </span>
      </span>
      <span>{value}</span>
    </span>
  );
}

function estimateHotspotsAvoided(route: NavigationRoute): string {
  const avoided = Math.max(0, Math.round((route.risk_sum - route.risk_p95) * 3));
  return `${avoided} higher-density segments`;
}

function normalizeExplanationLines(text: string): string[] {
  return text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => line.replace(/^[-*•]\s*/, ""));
}

export default function RouteCards({ routes, mode = "walking", riskAversion = 0.5 }: Props) {
  const [explanations, setExplanations] = useState<Record<string, string>>({});
  const [loadingRouteId, setLoadingRouteId] = useState<string | null>(null);
  const [explainError, setExplainError] = useState<Record<string, string>>({});

  const onExplain = async (route: NavigationRoute) => {
    setLoadingRouteId(route.route_id);
    setExplainError((prev) => ({ ...prev, [route.route_id]: "" }));
    try {
      const response = await explainRoute({
        route,
        context: {
          mode,
          risk_aversion: riskAversion,
        },
      });
      setExplanations((prev) => ({ ...prev, [route.route_id]: response.explanation }));
    } catch (err: any) {
      const detail = err?.response?.data?.detail ?? "Could not generate explanation.";
      setExplainError((prev) => ({ ...prev, [route.route_id]: String(detail) }));
    } finally {
      setLoadingRouteId(null);
    }
  };

  if (routes.length === 0) {
    return <p className="muted">No routes yet. Set origin and destination, then compute.</p>;
  }

  return (
    <div className="route-table-wrap">
      <table className="route-table" aria-label="Computed route options">
        <thead>
          <tr>
            <th>Route</th>
            <th>ETA</th>
            <th>Distance</th>
            <th>Risk p95</th>
            <th>Cost</th>
            <th>Why this route?</th>
          </tr>
        </thead>
        <tbody>
          {routes.map((route, idx) => (
            <tr key={route.route_id} className={route.recommended ? "row-recommended" : ""}>
              <td>
                <span className={`badge ${route.recommended ? "badge-primary" : "badge-muted"}`}>
                  {route.recommended ? "Recommended" : `Alternative ${idx + 1}`}
                </span>
              </td>
              <td>{etaText(route.duration_s)}</td>
              <td>{(route.distance_m / 1000).toFixed(2)} km</td>
              <td>{route.risk_p95.toFixed(3)}</td>
              <td>{route.total_cost.toFixed(3)}</td>
              <td>
                <details className="why-route">
                  <summary>Why this route?</summary>
                  <div className="why-route-content">
                    <InfoMetric
                      label="Time tradeoff"
                      value={`${Math.round(route.duration_s / 60)} min`}
                      help="Time tradeoff compared with other returned options."
                    />
                    <InfoMetric
                      label="Avoided hotspots"
                      value={estimateHotspotsAvoided(route)}
                      help="Approximate count of higher-density segments this route avoids."
                    />
                    <InfoMetric
                      label="Risk metric"
                      value={route.risk_metric_used ?? "risk_p95"}
                      help="Risk aggregate actually used by the scoring engine for this route set."
                    />
                  </div>
                </details>
                <div className="explain-action">
                  <Button
                    type="button"
                    size="sm"
                    variant="secondary"
                    onClick={() => void onExplain(route)}
                    disabled={loadingRouteId === route.route_id}
                  >
                    {loadingRouteId === route.route_id ? "Explaining..." : "Explain route with Gemini"}
                  </Button>
                </div>
                {explainError[route.route_id] && (
                  <p className="error-text explain-error">{explainError[route.route_id]}</p>
                )}
                {explanations[route.route_id] && (
                  <div className="ai-explanation">
                    <strong>Gemini summary</strong>
                    <ul>
                      {normalizeExplanationLines(explanations[route.route_id]).map((line, lineIdx) => (
                        <li key={`${route.route_id}-${lineIdx}`}>{line}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
