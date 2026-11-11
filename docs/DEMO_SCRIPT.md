# Demo script — fixed 15-minute path (VISION §17.1)

Use only these presets and sites; every expected number below comes from the committed snapshots
(`data/regions/sector_v/snapshots/flood_*.json`, `dev_compare.json`) and must match on screen. **Do not enter untested parameters live.**

## Before the session (T − 15 min)
1. Demo laptop on mains power, display mirrored, browser zoom 100 %.
2. `. .\scripts\env.ps1; .\scripts\dev.ps1` (or open the public URL and **wake the HF Space** ~3 min early).
3. The app opens without login (P20). Keep a second tab of the app open as a spare.
4. Quality: **High** on the RTX laptop; switch to **Standard** if the frame rate drops.
5. Local LLM (optional): Ollama window running (dev.ps1 starts it). If not, use **Template** — it's the default anyway.

## 0:00–1:30 · Problem and proposition (slides)
Interdependent systems; separate tools don't explain cross-system consequences; Hyperborea = one geospatial +
relationship model for a bounded pilot, with transparent scenarios.

## 1:30–3:00 · 3D digital twin and data layers
- App opens on Salt Lake Sector V (2.83 km²). Point at the provenance chips in **Layers** (Observed / Curated / Simulated).
- Click **Martin Burn Business Park** → info tag: **57.6 m**, *Height modelled (levels × 3.2 m)*. Inspector → Provenance.
- Toggle **Satellite**, **2D/3D**, then **Home**.

## 3:00–5:30 · Infrastructure and environment
- **Env → Weather**: live conditions + 72 h rain; ERA5 record: wettest day **169.9 mm (2019-08-17)**, IMD lines.
- **Env → Air**: NAQI category from CAMS (modelled) — read the badge.
- **Env → Land cover**: tick **NDVI** overlay (pilot mean **0.29**); mention WorldCover **71.5 % built-up**.
- Layers → **Drains (simulated)** + **Catchments**: banner *SIMULATED DRAINAGE NETWORK*. Click a drain → Manning formula with its inputs.
- **Inspect** (nothing selected): **Infrastructure health** — worst drains index ≈ **20–22**, reasons listed, simulated inputs flagged.

## 5:30–8:00 · Extreme-rainfall cascade (the key moment)
- **Disaster** → **Extreme 80×2h** → **Run**. Expect (≈ 1 s): **90 / 542** drains overloaded · **6.64 km** (75 edges) impassable ·
  **144** buildings above plinth · **12** transformers shut down · **109** buildings without power · **418** buildings isolated
  from hospitals, others **+2.47 min** on average.
- Click **International Institute of Photography** in the affected list → **Why?**: rain → drain **2.12 vs 1.88 m³/s** →
  ponding **1.00 m** → transformer **630 kVA** shutdown → *power lost, backup UNKNOWN* (+ access chain).
- **Plain-language explanation** → *Template* (or *Local LLM*, ≈ 5 s, grounding passed).
- **Access** tab → *Δ under scenario (extreme)*: magenta isolated pockets.
- Tick **AI quick-scan**, drag rain **15 → 80 mm/h**: map updates instantly; **Check vs full engine** → ≈ **99 %** agreement.
- **Open report** → print preview (scenario, metrics, affected table, assumptions, attributions).
- Contrast: **Moderate 15×3h** → only **5** drains overloaded.

## 8:00–10:30 · Development assessment
- **Develop** → **S2 · industrial**, commercial, **10 floors**, design storm → **Assess**:
  *Potentially unsuitable under current assumptions* — electrical **116 %** of the nearest transformer (fail), drainage conditional.
- **Compare A / B / C**: A S2 as proposed (index **0.82**) → **B S2 + detention + drain upsize + new transformer → Suitable (1.00)**
  → C alternative site S1 → still fails electrical (**227 %**): a 640 kVA block needs its own transformer anywhere.
  Read the *What changed* notes. Stress: "screening, never an approval".

## 10:30–12:30 · Relationship engine, provenance, validation
- Click a facility → **Graph** tab → *Flood chain* view (facility → roads → drains → network). Edge legend = rules.
- Show `docs/DATA_AUDIT.md` (PASS) and the model cards (`models/model_cards/`): surrogate F1 **0.85** vs baseline **0.32**;
  NDWI is *not ML*; LLM grounding check.

## 12:30–14:00 · Roadmap, impact, limitations (slides)
Real drain survey + pumping stations, LiDAR, calibrated hydraulics, utility feeders, observed waterlogging, more wards.

## Fallbacks
| Problem | Do this |
|---|---|
| Internet / Space down | Local `dev.ps1`; if the API is down too, the app opens the **offline snapshot** (amber badge): heavy + extreme presets, layers, development compare still work |
| Cesium slow | Quality → Standard; hide Buildings |
| LLM slow / missing | Use Template (default) |
| A number differs | Re-run the preset (results are deterministic); fall back to the snapshot numbers above |
| Total failure | Play the backup video (Teammate B) |
