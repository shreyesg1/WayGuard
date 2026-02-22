import { useEffect } from "react";
import { useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet.heat";

export interface HeatPoint {
  lat: number;
  lon: number;
  intensity: number;
}

interface Props {
  points: HeatPoint[];
}

export default function HeatLayer({ points }: Props) {
  const map = useMap();

  useEffect(() => {
    if (!points || points.length === 0) return;

    const layer = (L as any).heatLayer([], {
      radius: 14,
      blur: 12,
      maxZoom: 17,
      minOpacity: 0.18,
    });
    layer.addTo(map);

    const updateForViewport = () => {
      const zoom = map.getZoom();
      const bounds = map.getBounds().pad(0.2);
      const visible = points.filter((p) => bounds.contains(L.latLng(p.lat, p.lon)));

      // Progressive detail: fewer points + lower intensity when zoomed out.
      let stride = 1;
      if (zoom <= 10) stride = 10;
      else if (zoom <= 11) stride = 7;
      else if (zoom <= 12) stride = 5;
      else if (zoom <= 13) stride = 3;
      else if (zoom <= 14) stride = 2;

      const sampled: HeatPoint[] = [];
      for (let i = 0; i < visible.length; i += stride) {
        sampled.push(visible[i]);
      }

      const intensityScale =
        zoom <= 10 ? 0.25 : zoom <= 12 ? 0.45 : zoom <= 14 ? 0.7 : 1.0;
      const radius =
        zoom <= 10 ? 10 : zoom <= 12 ? 12 : zoom <= 14 ? 16 : 22;
      const blur = zoom <= 10 ? 8 : zoom <= 12 ? 10 : zoom <= 14 ? 12 : 16;
      const minOpacity = zoom <= 10 ? 0.12 : zoom <= 12 ? 0.16 : 0.22;

      layer.setOptions({ radius, blur, minOpacity, maxZoom: 17 });
      layer.setLatLngs(
        sampled.map((p) => [
          p.lat,
          p.lon,
          Math.max(0.03, Math.min(1, p.intensity * intensityScale)),
        ]),
      );
    };

    map.on("zoomend", updateForViewport);
    map.on("moveend", updateForViewport);
    updateForViewport();

    return () => {
      map.off("zoomend", updateForViewport);
      map.off("moveend", updateForViewport);
      map.removeLayer(layer);
    };
  }, [map, points]);

  return null;
}
