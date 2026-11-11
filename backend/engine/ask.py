"""P24 ask-the-twin: plain-language question → scenario intent → engine run → answer grounded in the result only.

Intent parsing: rule-based (always available, hosted mode) or local LLM via Ollama with a JSON schema; LLM intents are
accepted only if every number they contain appears in the question (or comes from a named preset). Answers: deterministic
template, or LLM phrasing that must pass `explain.grounded` (numbers must exist in the facts) — else the template.
"""
from __future__ import annotations

import json
import re
from collections.abc import Callable

import httpx

from .explain import grounded

FOCUS = ("summary", "hospitals", "facilities", "power", "access", "buildings")
FOCUS_WORDS = [
    ("hospitals", r"hospital|clinic|medical|ambulance|emergency care"),
    ("power", r"power|electric|transformer|outage|blackout|grid|substation"),
    ("access", r"road|street|route|traffic|access|reach|travel|drive|commute|cut off|isolated"),
    ("facilities", r"school|college|universit|fire station|police|facilit|metro|station"),
    ("buildings", r"building|house|home|plinth|flat|apartment|office"),
]
PRESET_WORDS = {"record_day": r"record|wettest|era5", "extreme": r"extreme|cloudburst|worst",
                "heavy": r"heavy|very wet", "design": r"design", "moderate": r"moderate|light|normal"}
NUM = r"(\d+(?:\.\d+)?)"
LABEL = "Answer generated from the rule engine's scenario result only (simulated networks, modelled rain) — not a forecast"


def parse_rule(q: str, presets: list[dict]) -> dict:
    t = q.lower()
    out: dict = {"preset": None, "rain_mm_h": None, "duration_h": None, "focus": "summary", "notes": []}
    if m := re.search(NUM + r"\s*(?:mm\s*/\s*h(?:r|our)?\b|mm\s*(?:per|an|a)\s*hour|mmph)", t):
        out["rain_mm_h"] = float(m.group(1))
    tot = re.search(NUM + r"\s*mm\b(?!\s*/|\s*(?:per|an|a)\s*hour)", t)
    if m := re.search(NUM + r"\s*(?:h|hr|hrs|hour|hours)\b", t):
        out["duration_h"] = float(m.group(1))
    if out["rain_mm_h"] is None and tot and out["duration_h"]:
        out["rain_mm_h"] = round(float(tot.group(1)) / out["duration_h"], 2)
        out["notes"].append(f"{tot.group(1)} mm over {out['duration_h']:g} h → uniform {out['rain_mm_h']} mm/h")
    if out["rain_mm_h"] is None:
        ids = {p["id"] for p in presets}
        out["preset"] = next((pid for pid, rx in PRESET_WORDS.items() if pid in ids and re.search(rx, t)), None)
    for focus, rx in FOCUS_WORDS:
        if re.search(rx, t):
            out["focus"] = focus
            break
    return out


SCHEMA = {"type": "object", "properties": {
    "preset": {"type": ["string", "null"], "enum": [None, "moderate", "design", "heavy", "extreme", "record_day"]},
    "rain_mm_h": {"type": ["number", "null"]}, "duration_h": {"type": ["number", "null"]},
    "focus": {"type": "string", "enum": list(FOCUS)}}, "required": ["preset", "rain_mm_h", "duration_h", "focus"]}
PARSE_SYSTEM = ("Turn the user's question about a flood scenario into JSON. rain_mm_h = rain intensity in mm per hour "
                "if the question states one, duration_h = hours if stated, otherwise null. preset only if the question "
                "names one (moderate, design, heavy, extreme, record_day). focus = what they ask about. Never invent numbers.")


def parse_llm(q: str, url: str, model: str, timeout: float = 30.0) -> dict | None:
    try:
        r = httpx.post(f"{url.rstrip('/')}/api/chat", timeout=timeout, json={
            "model": model, "stream": False, "think": False, "format": SCHEMA, "options": {"temperature": 0},
            "messages": [{"role": "system", "content": PARSE_SYSTEM}, {"role": "user", "content": q + " /no_think"}]})
        r.raise_for_status()
        it = json.loads(r.json()["message"]["content"])
    except Exception:  # noqa: BLE001 — no Ollama / bad JSON → rule parser
        return None
    nums = {float(x) for x in re.findall(NUM, q)}
    for k in ("rain_mm_h", "duration_h"):  # grounding for intents: numbers must come from the question
        if it.get(k) is not None and float(it[k]) not in nums:
            return None
    if it.get("focus") not in FOCUS:
        it["focus"] = "summary"
    return {**it, "notes": []}


def resolve_intent(it: dict, presets: list[dict], default_preset: str = "heavy") -> dict:
    """Fill gaps: rain without duration → 1 h; nothing → default preset (said in the notes)."""
    by_id = {p["id"]: p for p in presets}
    notes = list(it.get("notes", []))
    if it.get("rain_mm_h") is not None:
        rain = min(max(float(it["rain_mm_h"]), 0.5), 300.0)
        dur = float(it["duration_h"]) if it.get("duration_h") else 1.0
        if not it.get("duration_h"):
            notes.append("no duration given → 1 h assumed")
        params = {"preset": None, "preset_source_id": "syn_rain", "rain_mm_h": round(rain, 2),
                  "duration_h": round(min(max(dur, 0.25), 48.0), 2), "condition_scale": 1.0}
    else:
        pid = it.get("preset") if it.get("preset") in by_id else default_preset
        if not it.get("preset"):
            notes.append(f"no rain stated → '{pid}' preset assumed")
        p = by_id[pid]
        params = {"preset": pid, "preset_source_id": p["source_id"], "rain_mm_h": p["rain_mm_h"],
                  "duration_h": p["duration_h"], "condition_scale": 1.0}
    return {"params": params, "focus": it.get("focus") or "summary", "notes": notes}


def _ftype(fid: str, fac: dict) -> str:
    return (fac.get(fid) or {}).get("type") or (fid.split("_")[2] if fid.count("_") >= 3 else "facility")


def facts_for(res: dict, focus: str, fac: dict) -> dict:
    s = res["summary"]
    p = res["params"]
    base = {"scenario": f"{p['rain_mm_h']} mm/h for {p['duration_h']} h" + (f" (preset {p['preset']})" if p.get("preset") else ""),
            "drains_overloaded": s.get("drains_overloaded"), "drains_total": s.get("drains_total"),
            "data_status": "modelled scenario on simulated networks"}
    F = res["layers"].get("facilities", {})
    acc = (res.get("access") or {}).get("categories", {})
    if focus == "hospitals":
        hit = [{"name": fac.get(fid, {}).get("name") or fid, "state": v["state"].replace("_", " ")}
               for fid, v in F.items() if _ftype(fid, fac) in ("hospital", "clinic")]
        h = acc.get("hospital", {})
        return {**base, "hospitals_affected": len(hit), "hospitals": hit[:8],
                "buildings_cut_off_from_any_hospital": h.get("newly_isolated"),
                "buildings_with_slower_hospital_trip": h.get("buildings_slower"),
                "mean_extra_minutes_to_hospital": h.get("mean_delta_min"), "max_extra_minutes_to_hospital": h.get("max_delta_min")}
    if focus == "facilities":
        hit = [{"name": fac.get(fid, {}).get("name") or fid, "type": _ftype(fid, fac), "state": v["state"].replace("_", " ")}
               for fid, v in F.items()]
        return {**base, "facilities_affected": len(hit), "facilities": hit[:10]}
    if focus == "power":
        lost = [fac.get(fid, {}).get("name") or fid for fid, v in F.items() if v.get("power") == "loss"]
        return {**base, "transformers_shut_down": s.get("transformers_shutdown"),
                "buildings_without_power": s.get("buildings_power_loss"), "facilities_without_grid_power": lost[:8]}
    if focus == "access":
        h = acc.get("hospital", {})
        return {**base, "road_km_impassable": s.get("road_km_impassable"), "roads_impassable": s.get("roads_impassable"),
                "road_km_impaired": s.get("road_km_impaired"), "buildings_cut_off_from_any_hospital": h.get("newly_isolated"),
                "mean_extra_minutes_to_hospital": h.get("mean_delta_min")}
    if focus == "buildings":
        return {**base, "buildings_above_plinth": s.get("buildings_exposed"), "buildings_without_power": s.get("buildings_power_loss"),
                "max_ponding_m": s.get("max_depth_m")}
    return {**base, "road_km_impassable": s.get("road_km_impassable"), "buildings_above_plinth": s.get("buildings_exposed"),
            "transformers_shut_down": s.get("transformers_shutdown"), "buildings_without_power": s.get("buildings_power_loss"),
            "facilities_affected": s.get("facilities_affected"),
            "buildings_cut_off_from_any_hospital": acc.get("hospital", {}).get("newly_isolated")}


def template(f: dict, focus: str) -> str:
    head = f"Under {f['scenario']}, {f['drains_overloaded']} of {f['drains_total']} drains overload."
    if focus == "hospitals":
        names = "; ".join(f"{h['name']} ({h['state']})" for h in f["hospitals"]) or "none directly affected"
        return (f"{head} Hospitals affected: {f['hospitals_affected']} — {names}. "
                f"{f['buildings_cut_off_from_any_hospital'] or 0} buildings lose every road route to a hospital; "
                f"{f['buildings_with_slower_hospital_trip'] or 0} have a slower trip (mean +{f['mean_extra_minutes_to_hospital'] or 0} min).")
    if focus == "facilities":
        names = "; ".join(f"{x['name']} ({x['type']}, {x['state']})" for x in f["facilities"]) or "none"
        return f"{head} Facilities affected: {f['facilities_affected']} — {names}."
    if focus == "power":
        names = ", ".join(f["facilities_without_grid_power"]) or "none"
        return (f"{head} {f['transformers_shut_down']} transformers shut down; {f['buildings_without_power']} buildings lose "
                f"grid power. Facilities without grid power: {names}.")
    if focus == "access":
        return (f"{head} {f['road_km_impassable']} km of road become impassable ({f['roads_impassable']} segments) and "
                f"{f['road_km_impaired']} km impaired; {f['buildings_cut_off_from_any_hospital'] or 0} buildings are cut off "
                f"from every hospital (mean +{f['mean_extra_minutes_to_hospital'] or 0} min for the rest).")
    if focus == "buildings":
        return (f"{head} {f['buildings_above_plinth']} buildings have water above plinth (max ponding {f['max_ponding_m']} m); "
                f"{f['buildings_without_power']} lose grid power.")
    return (f"{head} {f['road_km_impassable']} km of road impassable, {f['buildings_above_plinth']} buildings above plinth, "
            f"{f['transformers_shut_down']} transformers shut down, {f['buildings_without_power']} buildings without power, "
            f"{f['facilities_affected']} facilities affected, {f['buildings_cut_off_from_any_hospital'] or 0} buildings cut off "
            f"from every hospital.")


ANSWER_SYSTEM = ("Answer the question in 2–3 short sentences for a city official, using ONLY the facts JSON. Copy numbers "
                 "exactly, write numbers as digits, never mention JSON field names. Report every non-zero impact in the "
                 "facts (e.g. buildings cut off from hospitals, extra minutes) — do not say 'no problem' if any impact "
                 "is non-zero. Say it is a scenario on simulated networks. No advice beyond the facts.")


def answer_llm(q: str, f: dict, url: str, model: str, timeout: float = 90.0) -> str:
    r = httpx.post(f"{url.rstrip('/')}/api/chat", timeout=timeout, json={
        "model": model, "stream": False, "think": False, "options": {"temperature": 0.2, "num_predict": 220},
        "messages": [{"role": "system", "content": ANSWER_SYSTEM},
                     {"role": "user", "content": f"Question: {q}\nFacts: {json.dumps(f, ensure_ascii=False)} /no_think"}]})
    r.raise_for_status()
    return r.json()["message"]["content"].strip()


def ask(q: str, presets: list[dict], run: Callable[[dict], dict], fac: dict, mode: str, url: str, model: str,
        llm_ok: bool) -> dict:
    use_llm = mode == "llm" and llm_ok
    it = (parse_llm(q, url, model) if use_llm else None)
    parser = "llm" if it else "rule"
    it = it or parse_rule(q, presets)
    ri = resolve_intent(it, presets)
    res = run(ri["params"])
    f = facts_for(res, ri["focus"], fac)
    text, answer_mode, rejected = template(f, ri["focus"]), "template", []
    if use_llm:
        try:
            cand = answer_llm(q, f, url, model)
            ok, bad = grounded(cand, f)
            if ok:
                text, answer_mode = cand, "llm"
            else:
                rejected = bad
        except Exception:  # noqa: BLE001
            rejected = ["llm unavailable"]
    return {"question": q, "label": LABEL, "data_status": "modelled", "parser": parser, "answer_mode": answer_mode,
            "grounding_rejected": rejected, "intent": {"focus": ri["focus"], **ri["params"]}, "notes": ri["notes"],
            "answer": text, "facts": f, "result_id": res["result_id"]}
