# CLAUDE.md — Hyperborea

## Every session
1. Read `planning.md` (start at §10 Status) and **only** the current `phases/Pxx.md`.
2. Don't read `docs/VISION.md`, `data/regions/*/raw/**`, `local/**`, `.venv/**`, `node_modules/**` unless the phase file says so.
3. For library/API docs use the **Context7 MCP** (`use context7`) before any web search.
4. In every new shell: `. .\scripts\env.ps1` (sets cache paths into `local/`, activates `.venv`).

## Hard rules
- **Git:** commit only at the end of a phase, after the user confirms. Message = one short line, `Pxx: <what>`. Use the existing git identity. **Never add Claude as co-author, no "Generated with" lines, no trailers.**
- **Never `git push` and never deploy** (Vercel / Hugging Face) unless the user says so in this session.
- **Done means done:** set a phase to `built` when code + tests pass; set `done` in planning.md §10 only after the user confirms it works. Then fill the Confirmed date.
- **Log everything** in `docs/LOG.md` (one entry per session). Decisions → `docs/DECISIONS.md`. Every new dataset → `docs/DATA_SOURCES.md` before it is used.
- **Provenance:** every feature carries `data_status` + `source_id` (planning §6). Never present simulated/curated data as observed. Scores are indices, not probabilities.
- **Everything stays in the project:** pip → `.venv`, npm → `node_modules`, models/datasets/caches/tools → `local/`. No global installs.
- **Shared schema (§6) and API contract (§8):** ask the user before changing.
- **AI components:** open-source + free only; record model name, version, licence in a model card.
- Windows + PowerShell native. No Docker locally.

## Token economy
- Edit, don't rewrite whole files. Don't re-read files you just wrote.
- Never print large files, GeoJSON, rasters or long logs; summarise (counts, head, tail).
- Prefer existing libraries over hand-written logic. Keep diffs small.
- Don't explore the repo broadly; the phase file lists what's in scope.
- Ask the user one compact question when blocked instead of guessing through many tool calls.

## Commands (create in P01)
```powershell
. .\scripts\env.ps1                 # env + venv
.\scripts\dev.ps1                   # backend :8000 + frontend :5173
pytest backend/tests -q             # backend tests
cd frontend; npm run build; npm test   # frontend build + vitest
```

## Phase-end checklist
1. Acceptance + tests in the phase file pass. 2. Screenshot(s) → `presentation/screens/Pxx_*.png`.
3. LOG.md entry (what, files, commands, versions, tests, known issues). 4. Status → `built`; tell the user what to click to verify.
5. After user confirms: status `done` + date, then local commit `Pxx: <what>`. 6. Redeploy only if the user asks.
