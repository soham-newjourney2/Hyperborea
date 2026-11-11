"""P24 ask-the-twin: rule parser phrasings, intent defaults, grounding of LLM answers, endpoint (template mode)."""
import pytest
from fastapi.testclient import TestClient

from backend.app.core.paths import GPKG
from backend.app.main import app
from backend.engine import ask as ea

PRESETS = [{"id": "moderate", "rain_mm_h": 15, "duration_h": 3, "source_id": "syn_rain"},
           {"id": "heavy", "rain_mm_h": 40, "duration_h": 2, "source_id": "syn_rain"},
           {"id": "extreme", "rain_mm_h": 80, "duration_h": 2, "source_id": "syn_rain"}]


@pytest.mark.parametrize("q,rain,dur,preset,focus", [
    ("Which hospitals lose access if 60 mm/h hits for 2 hours?", 60, 2, None, "hospitals"),
    ("what if 45mm per hour for 3 hrs", 45, 3, None, "summary"),
    ("120 mm in 3 hours - how many roads flood?", 40, 3, None, "access"),
    ("Power cuts in an extreme storm?", None, None, "extreme", "power"),
    ("heavy rain: are schools ok?", None, None, "heavy", "facilities"),
    ("Do buildings flood at 25 mm an hour?", 25, None, None, "buildings"),
    ("Is the metro station reachable during moderate rain?", None, None, "moderate", "access"),
    ("tell me everything", None, None, None, "summary"),
])
def test_rule_parser(q, rain, dur, preset, focus):
    it = ea.parse_rule(q, PRESETS)
    assert (it["rain_mm_h"], it["duration_h"], it["preset"], it["focus"]) == (rain, dur, preset, focus)


def test_resolve_defaults_and_clamps():
    r = ea.resolve_intent({"rain_mm_h": 999, "duration_h": None, "focus": "summary"}, PRESETS)
    assert r["params"]["rain_mm_h"] == 300 and r["params"]["duration_h"] == 1.0 and r["notes"]
    d = ea.resolve_intent({"rain_mm_h": None, "preset": None, "focus": "power"}, PRESETS)
    assert d["params"]["preset"] == "heavy" and "assumed" in d["notes"][0]


def test_llm_answer_with_invented_number_falls_back(monkeypatch):
    res = {"result_id": "r", "params": {"rain_mm_h": 40, "duration_h": 2, "preset": "heavy"},
           "summary": {"drains_overloaded": 5, "drains_total": 50, "transformers_shutdown": 2, "buildings_power_loss": 9},
           "layers": {"facilities": {}}, "access": {"categories": {}}}
    monkeypatch.setattr(ea, "parse_llm", lambda *a, **k: None)
    monkeypatch.setattr(ea, "answer_llm", lambda *a, **k: "Under heavy rain 77 transformers fail.")
    out = ea.ask("power during heavy rain?", PRESETS, lambda p: res, {}, "llm", "http://x", "m", llm_ok=True)
    assert out["answer_mode"] == "template" and "77" in out["grounding_rejected"] and "2 transformers shut down" in out["answer"]


@pytest.mark.skipif(not GPKG.with_name("drainage.gpkg").exists(), reason="run P06 pipelines")
def test_endpoint_template_mode():
    r = TestClient(app).post("/api/ask", json={"question": "Which hospitals are cut off at 80 mm/h for 2 h?", "mode": "template"}).json()
    assert r["parser"] == "rule" and r["answer_mode"] == "template" and r["intent"]["focus"] == "hospitals"
    assert r["facts"]["drains_total"] > 0 and str(r["facts"]["drains_overloaded"]) in r["answer"]
