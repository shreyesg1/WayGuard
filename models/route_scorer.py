from typing import Dict, List
import numpy as np
import pandas as pd

from models.risk_surface import RiskSurface
from routing.ors_client import RouteOption


def _normalize(values: pd.Series) -> pd.Series:
    min_v = values.min()
    max_v = values.max()
    if max_v <= min_v:
        return pd.Series(np.zeros(len(values)), index=values.index)
    return (values - min_v) / (max_v - min_v)


def _sample_spacing(mode: str) -> int:
    return 30 if mode == "walking" else 75


def score_routes(
    routes: List[RouteOption],
    risk_surface: RiskSurface,
    mode: str,
    risk_aversion: float,
    alpha_time: float = 0.6,
    beta_distance: float = 0.4,
    risk_aggregate: str = "p95",
) -> pd.DataFrame:
    rows: List[Dict] = []
    spacing = _sample_spacing(mode)

    for route in routes:
        risk_metrics = risk_surface.risk_for_polyline(
            route.geometry,
            sample_every_meters=spacing,
            aggregate=risk_aggregate,
        )
        rows.append(
            {
                "route_id": route.route_id,
                "duration_s": route.duration_s,
                "distance_m": route.distance_m,
                **risk_metrics,
            }
        )

    scored = pd.DataFrame(rows)
    if scored.empty:
        return scored

    # p95 can be zero across all routes when incidents are sparse at sample points.
    # Fall back to sum/max so risk still influences ranking when evidence exists.
    risk_metric_used = "risk_agg"
    if np.allclose(scored["risk_agg"].values, 0.0):
        if not np.allclose(scored["risk_sum"].values, 0.0):
            scored["risk_agg"] = scored["risk_sum"]
            risk_metric_used = "risk_sum"
        elif not np.allclose(scored["risk_max"].values, 0.0):
            scored["risk_agg"] = scored["risk_max"]
            risk_metric_used = "risk_max"

    scored["time_n"] = _normalize(scored["duration_s"])
    scored["distance_n"] = _normalize(scored["distance_m"])
    scored["risk_n"] = _normalize(scored["risk_agg"])

    gamma_risk = float(max(0.0, min(1.0, risk_aversion)))
    base = max(1e-6, 1.0 - gamma_risk)
    a = alpha_time * base
    b = beta_distance * base
    c = gamma_risk
    total = a + b + c
    a, b, c = a / total, b / total, c / total

    scored["total_cost"] = a * scored["time_n"] + b * scored["distance_n"] + c * scored["risk_n"]
    scored = scored.sort_values("total_cost", ascending=True).reset_index(drop=True)
    scored["rank"] = np.arange(1, len(scored) + 1)
    scored["recommended"] = scored["rank"] == 1
    scored["risk_metric_used"] = risk_metric_used
    return scored
