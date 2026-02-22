from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import math

import numpy as np
import pandas as pd

LatLon = Tuple[float, float]


def _haversine_m(a: LatLon, b: LatLon) -> float:
    r = 6371000.0
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def _interpolate(a: LatLon, b: LatLon, t: float) -> LatLon:
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def sample_polyline(polyline: List[LatLon], sample_every_meters: float) -> List[LatLon]:
    if not polyline:
        return []
    if len(polyline) == 1:
        return [polyline[0]]

    spacing = max(5.0, float(sample_every_meters))
    sampled: List[LatLon] = [polyline[0]]
    carry = spacing

    for i in range(1, len(polyline)):
        p0 = polyline[i - 1]
        p1 = polyline[i]
        seg_len = _haversine_m(p0, p1)
        if seg_len <= 0:
            continue

        dist = carry
        while dist <= seg_len:
            t = dist / seg_len
            sampled.append(_interpolate(p0, p1, t))
            dist += spacing
        carry = dist - seg_len

    if sampled[-1] != polyline[-1]:
        sampled.append(polyline[-1])
    return sampled


@dataclass
class RiskSurface:
    h3_resolution: int
    hex_risk: Dict[str, float]
    default_risk: float = 0.0
    overlap_rings: int = 0
    overlap_ring_decay: float = 0.6

    @classmethod
    def build_surface(
        cls,
        dfs: Dict[str, pd.DataFrame],
        config: Dict,
        time_window: int,
        mode: str,
        weights: Dict[str, float],
        category_filters: Optional[Dict[str, List[str]]] = None,
        now: Optional[datetime] = None,
    ) -> "RiskSurface":
        global_now = now or datetime.utcnow()
        routing_cfg = config.get("routing", {})
        resolution = int(routing_cfg.get("h3_resolution", 10))
        half_life_days = float(routing_cfg.get("decay_half_life_days", 30.0))
        spread_rings = int(routing_cfg.get("risk_spread_rings", 1))
        ring_decay = float(routing_cfg.get("risk_ring_decay", 0.55))
        use_time_decay = bool(routing_cfg.get("use_time_decay_for_navigation", False))
        overlap_rings = int(routing_cfg.get("overlap_rings_for_lookup", 1))
        overlap_ring_decay = float(routing_cfg.get("overlap_ring_decay", 0.6))

        try:
            import h3
        except Exception as exc:
            raise ImportError("Missing dependency 'h3'. Please add it to requirements and install.") from exc

        date_col_map = {
            "crime": "cmplnt_fr_dt",
            "complaints": "created_date",
            "health": "inspection_date",
        }
        category_col_map = {
            "crime": "ofns_desc",
            "complaints": "complaint_type",
            "health": "violation_code",
        }

        parts: List[pd.DataFrame] = []
        cutoff = pd.Timestamp(now) - pd.Timedelta(days=int(time_window))
        category_filters = category_filters or {}

        for dataset_key, df in dfs.items():
            if df is None or df.empty:
                continue
            dataset_weight = float(weights.get(dataset_key, 0.0))
            if dataset_weight <= 0:
                continue

            date_col = date_col_map.get(dataset_key)
            if not date_col or date_col not in df.columns:
                continue

            local = df.copy()
            local[date_col] = pd.to_datetime(local[date_col], errors="coerce")
            local["latitude"] = pd.to_numeric(local["latitude"], errors="coerce")
            local["longitude"] = pd.to_numeric(local["longitude"], errors="coerce")
            local = local.dropna(subset=["latitude", "longitude", date_col])

            # Anchor windowing/decay to each dataset's latest available timestamp.
            dataset_now = pd.to_datetime(local[date_col], errors="coerce").max()
            if pd.isna(dataset_now):
                dataset_now = pd.Timestamp(global_now)
            dataset_cutoff = dataset_now - pd.Timedelta(days=int(time_window))
            local = local[local[date_col] >= dataset_cutoff]

            category_col = category_col_map.get(dataset_key)
            allowed_categories = category_filters.get(dataset_key, [])
            if category_col and allowed_categories and category_col in local.columns:
                local = local[local[category_col].isin(allowed_categories)]

            if local.empty:
                continue

            if use_time_decay:
                age_days = (pd.Timestamp(dataset_now) - local[date_col]).dt.total_seconds() / 86400.0
                decay = np.exp(-np.log(2) * (age_days / max(1.0, half_life_days)))
                local["risk_contrib"] = dataset_weight * decay
            else:
                # Heatmap-like metric: incident presence density by dataset weight.
                local["risk_contrib"] = dataset_weight
            local["h3_cell"] = local.apply(
                lambda r: h3.latlng_to_cell(float(r["latitude"]), float(r["longitude"]), resolution),
                axis=1,
            )
            parts.append(local[["h3_cell", "risk_contrib"]])

        if not parts:
            return cls(h3_resolution=resolution, hex_risk={})

        all_rows = pd.concat(parts, ignore_index=True)
        base_hex_risk = all_rows.groupby("h3_cell")["risk_contrib"].sum().to_dict()

        # Build an area-based surface (heatmap-like) by spreading each cell's
        # contribution to neighboring rings. This avoids brittle exact-cell hits.
        if spread_rings <= 0 or not base_hex_risk:
            return cls(
                h3_resolution=resolution,
                hex_risk=base_hex_risk,
                overlap_rings=max(0, overlap_rings),
                overlap_ring_decay=max(0.0, min(1.0, overlap_ring_decay)),
            )

        smoothed: Dict[str, float] = {}
        for src_cell, src_value in base_hex_risk.items():
            smoothed[src_cell] = smoothed.get(src_cell, 0.0) + float(src_value)
            try:
                neighborhood = h3.grid_disk(src_cell, spread_rings)
            except Exception:
                continue
            for neighbor in neighborhood:
                if neighbor == src_cell:
                    continue
                try:
                    dist = h3.grid_distance(src_cell, neighbor)
                except Exception:
                    continue
                if dist <= 0:
                    continue
                weight = ring_decay ** dist
                smoothed[neighbor] = smoothed.get(neighbor, 0.0) + float(src_value) * weight

        return cls(
            h3_resolution=resolution,
            hex_risk=smoothed,
            overlap_rings=max(0, overlap_rings),
            overlap_ring_decay=max(0.0, min(1.0, overlap_ring_decay)),
        )

    def risk_at(self, lat: float, lon: float) -> float:
        try:
            import h3
        except Exception as exc:
            raise ImportError("Missing dependency 'h3'. Please install it.") from exc
        cell = h3.latlng_to_cell(float(lat), float(lon), self.h3_resolution)
        base = float(self.hex_risk.get(cell, self.default_risk))
        if self.overlap_rings <= 0:
            return base

        total = base
        try:
            neighbors = h3.grid_disk(cell, self.overlap_rings)
        except Exception:
            return total

        for n in neighbors:
            if n == cell:
                continue
            try:
                dist = h3.grid_distance(cell, n)
            except Exception:
                continue
            if dist <= 0:
                continue
            weight = self.overlap_ring_decay ** dist
            total += float(self.hex_risk.get(n, 0.0)) * weight
        return total

    def risk_for_polyline(
        self,
        polyline: List[LatLon],
        sample_every_meters: float,
        aggregate: str = "sum",
    ) -> Dict[str, float]:
        samples = sample_polyline(polyline, sample_every_meters)
        if not samples:
            return {
                "risk_sum": 0.0,
                "risk_p95": 0.0,
                "risk_max": 0.0,
                "risk_agg": 0.0,
                "sample_count": 0,
            }

        values = np.array([self.risk_at(lat, lon) for lat, lon in samples], dtype=float)
        risk_sum = float(values.sum())
        risk_p95 = float(np.percentile(values, 95))
        risk_max = float(values.max())

        if aggregate == "max":
            risk_agg = risk_max
        elif aggregate == "p95":
            risk_agg = risk_p95
        else:
            risk_agg = risk_sum

        return {
            "risk_sum": risk_sum,
            "risk_p95": risk_p95,
            "risk_max": risk_max,
            "risk_agg": risk_agg,
            "sample_count": int(values.size),
        }
