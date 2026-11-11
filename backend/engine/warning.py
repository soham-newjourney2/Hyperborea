"""P21 live early warning: 72 h hourly forecast rain → per-hour ML quick-scan → worst burst → one full engine run.

Pure functions; the API passes `quick(rain_mm_h, duration_h) -> predicted overloads` (surrogate) and
`run(rain_mm_h, duration_h) -> engine result`. Forecast-driven estimate on simulated networks — not an official warning.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta

LABEL = "Forecast-driven estimate — modelled rain (Open-Meteo), simulated networks; not an official warning"
LEVELS = ("none", "watch", "warning")


def best_window(rain: list[float], windows: list[int], min_rain: float,
                quick: Callable[[float, float], int]) -> dict | None:
    """Worst rolling burst: maximise surrogate-predicted overloads, then total rain. None if every window is dry."""
    best = None
    for w in windows:
        for i in range(0, len(rain) - w + 1):
            total = sum(rain[i:i + w])
            mean = total / w
            if mean < min_rain:
                continue
            est = quick(mean, float(w))
            key = (est, total)
            if best is None or key > best["key"]:
                best = {"key": key, "start": i, "hours": w, "rain_mm_h": round(mean, 2), "total_mm": round(total, 1),
                        "drains_overloaded_est": est}
    if best:
        best.pop("key")
    return best


def level_for(summary: dict, rules: dict) -> tuple[str, list[str]]:
    """First level whose any rule is met (warning before watch); returns the reasons too."""
    total = max(summary.get("drains_total") or 1, 1)
    vals = {"drains_overloaded_pct": 100 * (summary.get("drains_overloaded") or 0) / total,
            "buildings_hospital_isolated": summary.get("buildings_hospital_isolated") or 0,
            "facilities_affected": summary.get("facilities_affected") or 0,
            "road_km_impassable": summary.get("road_km_impassable") or 0}
    for lvl in ("warning", "watch"):
        why = [f"{k.replace('_', ' ')} {round(vals[k], 2)} ≥ {t}" for k, t in rules.get(lvl, {}).items()
               if k in vals and vals[k] >= t]
        if why:
            return lvl, why
    return "none", []


def outlook(hourly: list[dict], quick: Callable[[float, float], int], run: Callable[[float, float], dict],
            rules: dict) -> dict:
    rain = [float(h.get("precipitation") or 0.0) for h in hourly]
    min_rain = float(rules.get("min_rain_mm_h", 2.0))
    floor = float(rules.get("probability_floor_pct", 0))
    timeline = []
    for h, r in zip(hourly, rain):
        p = h.get("precipitation_probability")
        timeline.append({"time": h["time"], "rain_mm_h": round(r, 2), "probability_pct": p,
                         "unlikely": p is not None and p < floor,
                         "drains_overloaded_est": quick(r, 1.0) if r >= min_rain else 0})
    win = best_window(rain, list(rules.get("windows_h", [1, 2, 3])), min_rain, quick)
    out = {"label": LABEL, "data_status": "modelled", "source_ids": ["om_forecast", "ml_surrogate", "syn_drain"],
           "peak_rain_mm_h": round(max(rain), 2) if rain else 0.0, "total_rain_mm": round(sum(rain), 1),
           "hours": len(rain), "timeline": timeline, "window": None, "level": "none", "reasons": [],
           "summary": None, "top_affected": [], "result_id": None,
           "rules": {k: v for k, v in rules.items() if k == "levels"}}
    if win is None:
        out["headline"] = f"No flood risk expected in the next {len(rain)} h (peak {out['peak_rain_mm_h']} mm/h)."
        return out
    win["start_time"] = hourly[win["start"]]["time"]
    win["end_time"] = (datetime.fromisoformat(win["start_time"]) + timedelta(hours=win["hours"])).strftime("%Y-%m-%dT%H:%M")
    res = run(win["rain_mm_h"], float(win["hours"]))
    s = res["summary"]
    lvl, why = level_for(s, rules.get("levels", {}))
    keys = ("drains_overloaded", "drains_total", "road_km_impassable", "buildings_exposed", "transformers_shutdown",
            "buildings_power_loss", "facilities_affected", "buildings_hospital_isolated", "hospital_mean_delta_min")
    out.update(window=win, level=lvl, reasons=why, result_id=res["result_id"],
               summary={k: s.get(k) for k in keys},
               top_affected=[{k: a.get(k) for k in ("asset_id", "kind", "name", "state", "risk")} for a in res["affected"][:5]])
    when = f"{win['start_time'].replace('T', ' ')}–{win['end_time'][11:16]}"
    if lvl == "none":
        out["headline"] = (f"Rain expected {when}: {win['rain_mm_h']} mm/h for {win['hours']} h — "
                           f"network copes ({s.get('drains_overloaded', 0)} drains overloaded).")
    else:
        out["headline"] = (f"Flood {lvl.upper()} {when}: {win['rain_mm_h']} mm/h for {win['hours']} h → "
                           f"{s.get('drains_overloaded', 0)}/{s.get('drains_total', 0)} drains overloaded, "
                           f"{s.get('road_km_impassable', 0)} km roads impassable, "
                           f"{s.get('buildings_power_loss', 0) or 0} buildings without power.")
    return out
