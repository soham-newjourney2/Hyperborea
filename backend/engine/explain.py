"""P14 explainer: plain-language text grounded ONLY in engine output.

template (default, deterministic, the hosted mode) · llm (local Ollama, optional): the model sees only a facts JSON
built from the result; every number it writes must appear in those facts, else we fall back to the template.
"""
from __future__ import annotations

import json
import re

import httpx

NUM = re.compile(r"(?<![\w.])-?\d+(?:[.,]\d+)?")
WORD_NUM = re.compile(r"\b(?:eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|"
                      r"forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|billion|lakh|crore)\b", re.I)
UNSUPPORTED = ["degree", "celsius", "temperature", "death", "casualt", "injur", "fatal", "evacuat", "rupee", "₹", "dollar",
               "probability", "percent chance", "will definitely", "guarantee"]
STATE_WORDS = {"power_loss": "without grid power", "access_cut": "cut off from road access",
               "access_impaired": "harder to reach", "above_plinth": "flooded above its plinth",
               "shutdown": "shut down", "overloaded": "overloaded", "impassable": "impassable", "impaired": "impaired"}
SYSTEM = ("You explain flood-scenario results for city officials. Use ONLY the facts in the JSON the user gives. "
          "Do not add any number, place or cause that is not in the facts. Cite asset IDs exactly as written. "
          "Say clearly that the result is a scenario-based estimate, not a prediction, and state the data status. "
          "Write every number with digits, exactly as it appears in the facts, next to the quantity it belongs to. "
          "Write four to six short sentences of plain English, no lists, no markdown. "
          "Reply with the explanation only: never restate these instructions or describe your reasoning.")


def facts(result: dict, asset_id: str | None) -> dict:
    s = result["summary"]
    base = {"scenario": {k: result["params"][k] for k in ("preset", "rain_mm_h", "duration_h", "condition_scale")},
            "label": result["label"], "data_status": result["data_status"],
            "summary": {k: s[k] for k in ("drains_overloaded", "drains_total", "roads_impassable", "road_km_impassable",
                                          "buildings_exposed", "facilities_affected", "transformers_shutdown",
                                          "buildings_power_loss", "buildings_hospital_isolated", "hospital_mean_delta_min")
                        if k in s}}
    if asset_id:
        ex = result["explanations"].get(asset_id)
        if ex is None:
            raise KeyError(asset_id)
        base["asset"] = {"asset_id": asset_id, "kind": ex["kind"], "state": ex["state"], "trigger": ex["trigger"],
                         "chain": [st["label"] for st in ex["path"]] + [st["label"] for a in ex.get("also", [])
                                                                        for st in a["path"][-2:]],
                         "risk_index": ex["risk"]["index"], "confidence": ex["confidence"],
                         "assumptions": ex["assumptions"][:3], "mitigation": ex["mitigation"][:2]}
    return base


def _numbers(text: str) -> set[float]:
    return {float(x.replace(",", "")) if x.count(",") and len(x.split(",")[-1]) == 3 else float(x.replace(",", "."))
            for x in NUM.findall(text)}


def grounded(text: str, fact: dict) -> tuple[bool, list[str]]:
    """Every number in `text` must equal (to its own precision) some number in the facts; no spelled-out numbers
    above ten (they dodge the digit check) and no quantity/topic terms the facts never mention."""
    src = json.dumps(fact, ensure_ascii=False)
    have = _numbers(src)
    bad = [w for w in WORD_NUM.findall(text)]
    low = src.lower()
    bad += [t for t in UNSUPPORTED if re.search(rf"\b{t}", text, re.I) and t not in low]
    for raw in NUM.findall(text):
        v = float(raw.replace(",", "")) if raw.count(",") and len(raw.split(",")[-1]) == 3 else float(raw.replace(",", "."))
        dec = len(raw.split(".")[1]) if "." in raw else 0
        if not any(abs(v - h) <= 0.5 * 10 ** -dec + 1e-9 for h in have):
            bad.append(raw)
    return not bad, bad


def template(fact: dict) -> str:
    sc, s = fact["scenario"], fact["summary"]
    name = sc["preset"] or "custom"
    out = [f"Scenario '{name}': {sc['rain_mm_h']} mm/h of rain for {sc['duration_h']} h with drain condition × "
           f"{sc['condition_scale']} ({fact['label'].lower()}; {fact['data_status']})."]
    if "asset" not in fact:  # only facts that are present — the template never invents a number either
        if {"drains_overloaded", "drains_total"} <= s.keys():
            out.append(f"{s['drains_overloaded']} of {s['drains_total']} simulated drains overflow.")
        if {"roads_impassable", "road_km_impassable"} <= s.keys():
            out.append(f"{s['roads_impassable']} road segments ({s['road_km_impassable']} km) become impassable.")
        if "buildings_exposed" in s:
            out.append(f"{s['buildings_exposed']} buildings see water above plinth level.")
        if s.get("transformers_shutdown") and "buildings_power_loss" in s:
            out.append(f"{s['transformers_shutdown']} simulated transformers shut down, leaving {s['buildings_power_loss']} "
                       f"buildings without grid power.")
        if {"buildings_hospital_isolated", "hospital_mean_delta_min"} <= s.keys():
            out.append(f"{s['buildings_hospital_isolated']} buildings lose every drive route to a hospital; the rest are on "
                       f"average {s['hospital_mean_delta_min']} min slower (free-flow estimate).")
        return " ".join(out)
    a = fact["asset"]
    state = STATE_WORDS.get(a["state"], a["state"].replace("_", " "))
    out.append(f"{a['kind'].capitalize()} {a['asset_id']} is {state}: {a['trigger']}.")
    out.append("Chain: " + " → ".join(a["chain"]) + ".")
    out.append(f"Risk index {a['risk_index']} (an index, not a probability), confidence {a['confidence']}.")
    if a["mitigation"]:
        out.append("Possible mitigation: " + "; ".join(a["mitigation"]) + ".")
    return " ".join(out)


READABLE = {
    "drains_overloaded": "simulated drains that overflow", "drains_total": "simulated drains in the pilot",
    "roads_impassable": "road segments that become impassable", "road_km_impassable": "kilometres of impassable road",
    "buildings_exposed": "buildings with water above plinth level", "facilities_affected": "critical facilities affected",
    "transformers_shutdown": "simulated transformers that shut down",
    "buildings_power_loss": "buildings without grid power",
    "buildings_hospital_isolated": "buildings that lose every drive route to a hospital",
    "hospital_mean_delta_min": "average extra drive minutes to the nearest hospital for the others (free-flow)",
}


def llm_facts(fact: dict) -> dict:
    """Same numbers, self-describing keys — terse keys made the model misread quantities (e.g. minutes as degrees)."""
    out = {**fact, "summary": {READABLE.get(k, k): v for k, v in fact["summary"].items()}}
    sc = fact["scenario"]
    out["scenario"] = {"preset name": sc["preset"] or "custom", "rain intensity (mm/h)": sc["rain_mm_h"],
                       "rain duration (hours)": sc["duration_h"], "drain condition multiplier": sc["condition_scale"]}
    return out


def llm(fact: dict, url: str, model: str, timeout: float = 90.0) -> str:
    fact = llm_facts(fact)
    r = httpx.post(f"{url.rstrip('/')}/api/chat", timeout=timeout, json={
        "model": model, "stream": False, "think": False,
        "options": {"temperature": 0.2, "num_predict": 320},
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": "/no_think\nFacts:\n" + json.dumps(fact, ensure_ascii=False, indent=1)}]})
    r.raise_for_status()
    text = r.json()["message"]["content"]
    return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()


def llm_status(url: str, model: str) -> dict:
    try:
        tags = httpx.get(f"{url.rstrip('/')}/api/tags", timeout=2).json().get("models", [])
        names = [t["name"] for t in tags]
        return {"available": bool(model) and any(n == model or n.startswith(model + ":") for n in names),
                "server": True, "models": names, "model": model}
    except Exception:  # noqa: BLE001 — Ollama not running
        return {"available": False, "server": False, "models": [], "model": model}


def explain(result: dict, asset_id: str | None, mode: str, url: str, model: str) -> dict:
    fact = facts(result, asset_id)
    tmpl = template(fact)
    if mode != "llm":
        return {"text": tmpl, "mode": "template", "grounded": True, "model": None, "facts": fact}
    try:
        text = llm(fact, url, model)
    except Exception as e:  # noqa: BLE001
        return {"text": tmpl, "mode": "template", "grounded": True, "model": None, "facts": fact,
                "fallback_reason": f"local LLM unavailable ({type(e).__name__})"}
    ok, bad = grounded(text, fact)
    if not ok:
        return {"text": tmpl, "mode": "template", "grounded": True, "model": model, "facts": fact,
                "fallback_reason": f"LLM output had numbers not in the facts: {', '.join(bad[:5])}", "rejected_text": text}
    return {"text": text, "mode": "llm", "grounded": True, "model": model, "facts": fact}
