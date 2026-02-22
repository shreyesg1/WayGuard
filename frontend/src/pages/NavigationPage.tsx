import { useMemo, useState } from "react";
import AddressAutocomplete from "../components/AddressAutocomplete";
import RouteCards from "../components/RouteCards";
import RouteMap from "../components/RouteMap";
import { computeNavigation } from "../api/client";
import type { GeocodeSuggestion, LatLon, NavigationResponse, TravelMode } from "../types";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";
import Skeleton from "../components/ui/Skeleton";

const DEFAULT_DESTINATION = "";

function sampleWaypointsForGoogle(route: NavigationResponse["routes"][number], maxWaypoints: number): string[] {
  const points = route.geometry ?? [];
  if (points.length <= 2 || maxWaypoints <= 0) return [];

  const interior = points.slice(1, -1);
  if (interior.length <= maxWaypoints) {
    return interior.map((p) => `${p.lat},${p.lon}`);
  }

  const sampled: string[] = [];
  for (let i = 0; i < maxWaypoints; i += 1) {
    const idx = Math.floor(((i + 1) * interior.length) / (maxWaypoints + 1));
    const point = interior[Math.max(0, Math.min(interior.length - 1, idx))];
    sampled.push(`${point.lat},${point.lon}`);
  }
  return sampled;
}

function buildGoogleMapsExportUrl(
  route: NavigationResponse["routes"][number],
  mode: TravelMode,
  origin?: LatLon,
  destination?: LatLon,
): string {
  const first = route.geometry[0];
  const last = route.geometry[route.geometry.length - 1];
  if (!first || !last) return "";

  const originStr = `${origin?.lat ?? first.lat},${origin?.lon ?? first.lon}`;
  const destinationStr = `${destination?.lat ?? last.lat},${destination?.lon ?? last.lon}`;
  const waypoints = sampleWaypointsForGoogle(route, 10).join("|");
  const params = new URLSearchParams({
    api: "1",
    origin: originStr,
    destination: destinationStr,
    travelmode: mode === "driving" ? "driving" : "walking",
  });
  if (waypoints) params.set("waypoints", waypoints);
  return `https://www.google.com/maps/dir/?${params.toString()}`;
}

export default function NavigationPage() {
  const [originInput, setOriginInput] = useState("");
  const [destinationInput, setDestinationInput] = useState(DEFAULT_DESTINATION);
  const [origin, setOrigin] = useState<LatLon | undefined>(undefined);
  const [destination, setDestination] = useState<LatLon | undefined>(undefined);
  const [mode, setMode] = useState<TravelMode>("walking");
  const [alternatives, setAlternatives] = useState(3);
  const [timeWindow, setTimeWindow] = useState(30);
  const [riskAversion, setRiskAversion] = useState(0.5);
  const [useCrime, setUseCrime] = useState(true);
  const [useComplaints, setUseComplaints] = useState(false);
  const [useHealth, setUseHealth] = useState(false);
  const [wCrime, setWCrime] = useState(1.0);
  const [wComplaints, setWComplaints] = useState(0.4);
  const [wHealth, setWHealth] = useState(0.3);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<NavigationResponse | null>(null);

  const hasValidRouteInputs = useMemo(() => !!origin && !!destination, [origin, destination]);
  const contribution = useMemo(() => {
    const total = wCrime + wComplaints + wHealth;
    if (total <= 0) return { crime: 0, complaints: 0, health: 0 };
    return {
      crime: (wCrime / total) * 100,
      complaints: (wComplaints / total) * 100,
      health: (wHealth / total) * 100,
    };
  }, [wCrime, wComplaints, wHealth]);
  const selectedRoute = useMemo(
    () => result?.routes?.find((r) => r.recommended) ?? result?.routes?.[0],
    [result],
  );
  const googleMapsExportUrl = useMemo(
    () => (selectedRoute ? buildGoogleMapsExportUrl(selectedRoute, mode, result?.origin ?? origin, result?.destination ?? destination) : ""),
    [selectedRoute, mode, result, origin, destination],
  );

  const useCurrentLocation = () => {
    if (!navigator.geolocation) {
      setError("Geolocation is not supported by your browser.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const selected = { lat: position.coords.latitude, lon: position.coords.longitude };
        setOrigin(selected);
        setOriginInput(`${selected.lat.toFixed(5)}, ${selected.lon.toFixed(5)}`);
        setError(null);
      },
      () => setError("Could not get current location. Check browser permissions."),
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 30000 },
    );
  };

  const onSuggestionSelect = (setter: (value: LatLon) => void) => (s: GeocodeSuggestion) => {
    setter({ lat: s.lat, lon: s.lon });
  };

  const resetPlanner = () => {
    setOriginInput("");
    setDestinationInput("");
    setOrigin(undefined);
    setDestination(undefined);
    setMode("walking");
    setAlternatives(3);
    setTimeWindow(30);
    setRiskAversion(0.5);
    setUseCrime(true);
    setUseComplaints(false);
    setUseHealth(false);
    setWCrime(1.0);
    setWComplaints(0.4);
    setWHealth(0.3);
    setError(null);
    setResult(null);
  };

  const compute = async () => {
    if (!origin || !destination) {
      setError("Please select both origin and destination from suggestions.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await computeNavigation({
        origin,
        destination,
        mode,
        alternatives,
        time_window_days: timeWindow,
        risk_aversion: riskAversion,
        use_crime: useCrime,
        use_complaints: useComplaints,
        use_health: useHealth,
        w_crime: wCrime,
        w_complaints: wComplaints,
        w_health: wHealth,
      });
      setResult(response);
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Unable to compute routes.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-layout nav-layout">
      <Card
        className="nav-control-card"
        title="Safer Route Planner"
        subtitle="Find lower incident-density paths with transparent tradeoffs."
      >
        <div className="form-grid">
          <div className="planner-section">
            <h4>Origin</h4>
            <div className="button-row">
              <Button variant="secondary" onClick={useCurrentLocation} type="button">Use current location</Button>
            </div>
            <AddressAutocomplete
              label="Origin address"
              value={originInput}
              placeholder="Type a place or address"
              onValueChange={(v) => {
                setOriginInput(v);
                setOrigin(undefined);
              }}
              onSelectSuggestion={onSuggestionSelect(setOrigin)}
            />
          </div>
          <div className="planner-section">
            <h4>Destination</h4>
            <AddressAutocomplete
              label="Destination"
              value={destinationInput}
              placeholder="Type a destination"
              onValueChange={(v) => {
                setDestinationInput(v);
                setDestination(undefined);
              }}
              onSelectSuggestion={onSuggestionSelect(setDestination)}
            />
          </div>
          <div className="planner-section">
            <h4>Mode</h4>
            <div className="field">
              <label>Travel mode</label>
              <select value={mode} onChange={(e) => setMode(e.target.value as TravelMode)} aria-label="Travel mode">
                <option value="walking">Walking</option>
                <option value="driving">Driving</option>
              </select>
            </div>
          </div>
          <div className="planner-section">
            <h4>Options</h4>
            <div className="field">
              <label>Alternatives ({alternatives})</label>
              <input
                type="range"
                min={2}
                max={5}
                step={1}
                value={alternatives}
                onChange={(e) => setAlternatives(Number(e.target.value))}
                aria-label="Number of alternatives"
              />
              <span className="field-hint">Discrete steps from 2 to 5 route options.</span>
            </div>
            <div className="field">
              <label>Incident window (days)</label>
              <select value={timeWindow} onChange={(e) => setTimeWindow(Number(e.target.value))}>
                <option value={7}>7</option>
                <option value={30}>30</option>
                <option value={90}>90</option>
              </select>
            </div>
            <div className="field">
              <label>
                Risk aversion ({riskAversion.toFixed(2)})
                <span
                  className="inline-help"
                  title="0 prioritizes faster/shorter routes. 0.5 is balanced. 1 prioritizes lower incident-density exposure."
                >
                  Fastest ↔ Balanced ↔ Lowest Risk
                </span>
              </label>
              <input type="range" min={0} max={1} step={0.05} value={riskAversion} onChange={(e) => setRiskAversion(Number(e.target.value))} />
            </div>
          </div>
        </div>
        <details className="fieldset" open>
          <summary>Dataset toggles & weights</summary>
          <div className="checkbox-row">
            <label><input type="checkbox" checked={useCrime} onChange={(e) => setUseCrime(e.target.checked)} /> NYPD complaints</label>
            <label><input type="checkbox" checked={useComplaints} onChange={(e) => setUseComplaints(e.target.checked)} /> 311 complaints</label>
            <label><input type="checkbox" checked={useHealth} onChange={(e) => setUseHealth(e.target.checked)} /> Restaurant inspections</label>
          </div>
          <div className="form-grid">
            <div className="field">
              <label>NYPD weight</label>
              <input type="range" min={0} max={1} step={0.05} value={wCrime} onChange={(e) => setWCrime(Number(e.target.value))} />
            </div>
            <div className="field">
              <label>311 weight</label>
              <input type="range" min={0} max={1} step={0.05} value={wComplaints} onChange={(e) => setWComplaints(Number(e.target.value))} />
            </div>
            <div className="field">
              <label>Inspection weight</label>
              <input type="range" min={0} max={1} step={0.05} value={wHealth} onChange={(e) => setWHealth(Number(e.target.value))} />
            </div>
          </div>
        </details>

        <div className="button-row planner-actions">
          <Button variant="primary" disabled={!hasValidRouteInputs || loading} onClick={compute} type="button">
            {loading ? "Computing..." : "Compute Routes"}
          </Button>
          <Button variant="ghost" onClick={resetPlanner} type="button">
            Reset
          </Button>
        </div>
        {error && <p className="error-text">{error}</p>}
      </Card>

      <div className="nav-right-rail">
        <Card className="nav-map-card" title="Live Route Map" subtitle="Recommended route highlighted">
          <div className="card-title-row map-title-row">
            <div className="route-legend">
              <span className="legend-item"><span className="legend-swatch recommended" /> Recommended</span>
              <span className="legend-item"><span className="legend-swatch alternate" /> Alternative</span>
            </div>
            {googleMapsExportUrl && (
              <a
                className="map-export-btn-inline"
                href={googleMapsExportUrl}
                target="_blank"
                rel="noopener noreferrer"
                aria-label="Export selected route to Google Maps"
                title="Open selected route in Google Maps"
              >
                Export to Google Maps
              </a>
            )}
          </div>
          <div className="map-hero-wrap">
            {loading ? (
              <div className="map-skeleton">
                <Skeleton className="skeleton-map" />
              </div>
            ) : (
              <RouteMap
                origin={result?.origin ?? origin}
                destination={result?.destination ?? destination}
                routes={result?.routes ?? []}
              />
            )}
            <div className="map-info-tray">
              <div className="tray-title">Route Summary</div>
              {result?.routes?.[0] ? (
                <>
                  <div className="tray-stats">
                    <span>ETA: {Math.round(result.routes[0].duration_s / 60)} min</span>
                    <span>Distance: {(result.routes[0].distance_m / 1000).toFixed(2)} km</span>
                    <span>Risk p95: {result.routes[0].risk_p95.toFixed(3)}</span>
                  </div>
                  <div className="contrib-stack" aria-label="Dataset contribution weights">
                    <div className="seg crime" style={{ width: `${contribution.crime}%` }} title={`NYPD ${contribution.crime.toFixed(1)}%`} />
                    <div className="seg complaints" style={{ width: `${contribution.complaints}%` }} title={`311 ${contribution.complaints.toFixed(1)}%`} />
                    <div className="seg health" style={{ width: `${contribution.health}%` }} title={`Health ${contribution.health.toFixed(1)}%`} />
                  </div>
                </>
              ) : (
                <p className="muted">Compute a route to see summary metrics.</p>
              )}
            </div>
          </div>
        </Card>

        <Card className="nav-route-card" title="Route Options">
          {loading ? (
            <div className="route-table-skeleton">
              <Skeleton className="skeleton-row" />
              <Skeleton className="skeleton-row" />
              <Skeleton className="skeleton-row" />
            </div>
          ) : result?.routes?.length ? (
            <RouteCards routes={result.routes} mode={mode} riskAversion={riskAversion} />
          ) : (
            <div className="empty-state">
              <p>Set an origin and destination, then compute routes.</p>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
