from __future__ import annotations

import os
from typing import Any, Dict, List

import requests


class RouteExplainerService:
    def __init__(self) -> None:
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        model = os.getenv("GEMINI_MODEL", "").strip()
        self.models: List[str] = (
            [model]
            if model
            else ["gemini-2.0-flash", "gemini-1.5-flash-latest", "gemini-1.5-flash"]
        )

    def explain_route(self, payload: Dict[str, Any]) -> str:
        if not self.api_key:
            raise ValueError("Missing GEMINI_API_KEY in backend environment.")

        route = payload.get("route", {}) or {}
        context = payload.get("context", {}) or {}

        prompt = self._build_prompt(route=route, context=context)
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 512,
            },
        }
        last_error: str | None = None
        for model in self.models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            try:
                response = requests.post(
                    url,
                    params={"key": self.api_key},
                    json=body,
                    timeout=30,
                )
                if response.status_code == 404:
                    # Model not available for this account/region; try next candidate.
                    last_error = f"Model {model} not found."
                    continue
                if response.status_code == 401:
                    raise RuntimeError("Gemini API key is invalid or unauthorized.")
                response.raise_for_status()
                data = response.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                if self._is_sufficient_explanation(text):
                    return text
                return self._fallback_explanation(route=route, context=context)
            except requests.HTTPError:
                # Avoid leaking full request URL (which includes API key in query params).
                last_error = f"Gemini request failed with status {response.status_code}."
                continue
            except Exception as exc:
                last_error = str(exc)
                continue

        if last_error and "unauthorized" in last_error.lower():
            raise RuntimeError(last_error)
        # If models are unavailable, still return deterministic explanation for UX continuity.
        return self._fallback_explanation(route=route, context=context)

    @staticmethod
    def _is_sufficient_explanation(text: str) -> bool:
        lowered = text.lower()
        has_tradeoff = ("risk" in lowered) and ("time" in lowered or "eta" in lowered)
        bullet_lines = [
            ln for ln in text.splitlines()
            if ln.strip().startswith(("-", "*", "•"))
        ]
        return has_tradeoff and len(bullet_lines) >= 3

    @staticmethod
    def _fallback_explanation(route: Dict[str, Any], context: Dict[str, Any]) -> str:
        mode = str(context.get("mode", "walking"))
        risk_aversion = float(context.get("risk_aversion", 0.5))
        eta_min = round(float(route.get("duration_s", 0.0)) / 60.0)
        dist_km = float(route.get("distance_m", 0.0)) / 1000.0
        risk_p95 = float(route.get("risk_p95", 0.0))
        risk_max = float(route.get("risk_max", 0.0))
        return (
            f"- This {mode} route is estimated at about {eta_min} minutes over {dist_km:.2f} km, "
            "and was chosen as a practical time vs risk tradeoff rather than only the shortest path.\n"
            f"- Its risk profile (p95 {risk_p95:.3f}, max {risk_max:.3f}) indicates pockets of higher incident density, "
            "but avoids some higher-exposure segments compared with a purely time-optimized option.\n"
            f"- With risk aversion set to {risk_aversion:.2f}, this recommendation balances efficiency and lower exposure; "
            "increase toward 1.0 for lower-risk routes or decrease toward 0 for faster routes."
        )

    @staticmethod
    def _build_prompt(route: Dict[str, Any], context: Dict[str, Any]) -> str:
        mode = str(context.get("mode", "walking"))
        risk_aversion = float(context.get("risk_aversion", 0.5))
        recommended = bool(route.get("recommended", False))
        eta_min = round(float(route.get("duration_s", 0.0)) / 60.0)
        dist_km = float(route.get("distance_m", 0.0)) / 1000.0
        risk_p95 = float(route.get("risk_p95", 0.0))
        risk_max = float(route.get("risk_max", 0.0))
        risk_sum = float(route.get("risk_sum", 0.0))
        risk_metric_used = str(route.get("risk_metric_used", "risk_p95"))

        return (
            "You are explaining a safer-route recommendation in plain language.\n"
            "Use neutral language like 'higher incident density'.\n"
            "Return exactly 3 bullet points, each 1-2 sentences.\n"
            "Include: (1) time/distance tradeoff, (2) risk exposure interpretation, "
            "(3) who this route suits given risk aversion.\n"
            "Avoid making guarantees about safety.\n\n"
            "Do not truncate mid-sentence.\n\n"
            f"Trip mode: {mode}\n"
            f"Route type: {'recommended' if recommended else 'alternative'}\n"
            f"ETA minutes: {eta_min}\n"
            f"Distance km: {dist_km:.2f}\n"
            f"Risk p95: {risk_p95:.3f}\n"
            f"Risk max: {risk_max:.3f}\n"
            f"Risk sum: {risk_sum:.3f}\n"
            f"Risk metric used by scorer: {risk_metric_used}\n"
            f"User risk aversion (0 fastest, 1 lowest risk): {risk_aversion:.2f}\n"
        )
