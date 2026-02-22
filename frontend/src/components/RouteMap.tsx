import { useEffect } from "react";
import { MapContainer, Marker, Polyline, TileLayer, Tooltip, useMap } from "react-leaflet";
import type { LatLon, NavigationRoute } from "../types";

interface Props {
  origin?: LatLon;
  destination?: LatLon;
  routes: NavigationRoute[];
}

function fmtDuration(seconds: number): string {
  const mins = Math.round(seconds / 60);
  if (mins < 60) return `${mins} min`;
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return `${h}h ${m}m`;
}

function fmtDistance(distanceM: number): string {
  return `${(distanceM / 1000).toFixed(2)} km`;
}

export default function RouteMap({ origin, destination, routes }: Props) {
  const center: [number, number] = origin
    ? [origin.lat, origin.lon]
    : destination
      ? [destination.lat, destination.lon]
      : [40.7128, -74.006];

  return (
    <div className="map-shell">
      <MapContainer center={center} zoom={13} className="map-container" zoomControl={false} preferCanvas>
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; OpenStreetMap contributors &copy; CARTO'
        />
        <FitToRoute origin={origin} destination={destination} routes={routes} />
        {origin && <Marker position={[origin.lat, origin.lon]} />}
        {destination && <Marker position={[destination.lat, destination.lon]} />}
        {routes.map((route) => (
          <Polyline
            key={route.route_id}
            positions={route.geometry.map((p) => [p.lat, p.lon] as [number, number])}
            pathOptions={{
              color: route.recommended ? "#2b8cbe" : "#7d8591",
              weight: route.recommended ? 7 : 4,
              opacity: route.recommended ? 0.9 : 0.65,
              dashArray: route.recommended ? undefined : "7 9",
            }}
          >
            <Tooltip sticky>
              {route.recommended ? "Recommended" : "Alternative"} - {fmtDuration(route.duration_s)} -{" "}
              {fmtDistance(route.distance_m)}
            </Tooltip>
          </Polyline>
        ))}
      </MapContainer>
    </div>
  );
}

function FitToRoute({ origin, destination, routes }: Props) {
  const map = useMap();

  useEffect(() => {
    const points: Array<[number, number]> = [];
    if (origin) points.push([origin.lat, origin.lon]);
    if (destination) points.push([destination.lat, destination.lon]);
    for (const route of routes) {
      for (const p of route.geometry) {
        points.push([p.lat, p.lon]);
      }
    }
    if (points.length < 2) return;
    map.fitBounds(points, { padding: [40, 40] });
  }, [map, origin, destination, routes]);

  return null;
}
