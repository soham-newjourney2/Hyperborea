# Model card — Hyperborea plain-language explainer (`/explain`)

**What it is:** a two-mode explainer that turns flood-engine output into short plain-English text.

| Mode | What runs | Where | Default |
|---|---|---|---|
| `template` | deterministic Python template over the result's own facts | everywhere (hosted API) | **yes** |
| `llm` | **Qwen3-4B-Instruct-2507** (`qwen3:4b-instruct-2507-q4_K_M`, 4-bit, 2.5 GB) via **Ollama v0.40.15** portable | local laptop only (RTX 4050 6 GB, 100 % GPU, ~5 s per answer) | no |

| | |
|---|---|
| Model licence | **Apache-2.0** — verified on huggingface.co/Qwen/Qwen3-4B-Instruct-2507 (2026-11-07); non-thinking model |
| Runtime licence | Ollama — MIT |
| Install | `scripts/install_ollama.py` → `local/tools/ollama`; models in `local/ollama/models` (`OLLAMA_MODELS`); nothing installed globally |
| Inputs | only a facts JSON built from one engine result (scenario, summary counts, the asset's Why? chain, risk index, assumptions, mitigation) |

## Grounding (every LLM answer, before it is shown)
1. Every number in the output must equal a number in the facts (to the precision written).
2. No spelled-out numbers above ten (they would dodge check 1).
3. No unsupported quantity/topic terms absent from the facts (degrees, temperature, deaths, casualties, evacuation,
   money, probability, guarantees …).
4. Any failure → the deterministic template is returned instead (`fallback_reason` says why; `rejected_text` kept for audit).

Prompt rules: use only the given facts, cite asset IDs exactly, write numbers as digits, say "scenario-based estimate,
not a prediction", state the data status. Facts use self-describing keys (terse keys made the model misread minutes as
degrees during testing — caught by check 3).

## Observed during testing (2026-11-07)
- `qwen3:4b` (thinking build) leaked its reasoning into the answer → rejected by the checks; switched to the
  non-thinking Instruct-2507 build.
- Instruct-2507 answers for the extreme scenario and an affected facility passed grounding and read naturally.
- One answer said "one access road is impaired" where the facts said "1 impassable + 0 impaired": the checks verify
  numbers and terms, **not meaning**. The template therefore stays the default and the only mode on the hosted URL.

## Limitations
- Meaning-level errors (swapping which quantity a correct number belongs to) can pass the checks.
- Answers describe a simulated network and a rule-based engine; they inherit every assumption of both.
- Not available on the hosted demo (no GPU; LLM toggle shows "not installed").
