"""P15 data audit → docs/DATA_AUDIT.md (exit 1 on any failure).

Checks every served layer (GPKGs + curated/synthetic GeoJSON, exactly what the API loads):
asset_id present + unique · data_status valid · source_id registered in docs/DATA_SOURCES.md · simulated layers are
labelled simulated/curated · simulated/modelled features state assumptions. Repo: .env + local-only files untracked,
no obvious secrets tracked, committed data/model files < 5 MB.
Run:  python scripts/audit_data.py
"""
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.core.provenance import DataStatus  # noqa: E402
from backend.app.services.layer_store import LayerStore  # noqa: E402

OUT = ROOT / "docs" / "DATA_AUDIT.md"
MUST_BE_SIMULATED = {"drains", "drain_nodes", "catchments", "transformers", "feeders", "water_quality"}
LOCAL_ONLY = ("CLAUDE.md", "planning.md", ".mcp.json", ".claude/", "phases/", "docs/LOG.md")
SECRET = re.compile(r"(hf_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|"
                    r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----)")


def main() -> int:
    sources = set(re.findall(r"^### (\S+)", (ROOT / "docs" / "DATA_SOURCES.md").read_text(encoding="utf-8"), re.M))
    valid = {s.value for s in DataStatus}
    store = LayerStore.load()
    rows, fails, all_ids = [], [], Counter()
    for name, lyr in store.layers.items():
        g = lyr.gdf
        n = len(g)
        status = Counter(g.data_status)
        srcs = set(g.source_id.dropna())
        probs = []
        if g.asset_id.isna().any():
            probs.append("missing asset_id")
        if not g.asset_id.is_unique:
            probs.append("duplicate asset_id")
        if set(status) - valid:
            probs.append(f"invalid data_status {sorted(set(status) - valid)}")
        if g.source_id.isna().any():
            probs.append("missing source_id")
        if srcs - sources:
            probs.append(f"unregistered source_id {sorted(srcs - sources)}")
        if name in MUST_BE_SIMULATED and set(status) - {"simulated", "curated"}:
            probs.append(f"must be simulated, has {dict(status)}")
        needs = g[g.data_status.isin(["simulated", "modelled"])]
        if len(needs) and (needs.assumptions.fillna("").str.len() == 0).any():
            probs.append("simulated/modelled features without assumptions")
        all_ids.update(g.asset_id)
        rows.append((name, n, dict(status), sorted(srcs), "PASS" if not probs else "FAIL: " + "; ".join(probs)))
        fails += [f"{name}: {p}" for p in probs]
    dup_across = [a for a, c in all_ids.items() if c > 1]
    if dup_across:
        fails.append(f"asset_id shared across layers: {dup_across[:5]}")

    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.splitlines()
    repo = []
    if any(t == ".env" or t.endswith("/.env") for t in tracked):
        repo.append("FAIL: .env is tracked")
    leaked = [t for t in tracked if t.startswith(LOCAL_ONLY) or t in LOCAL_ONLY]
    if leaked:
        repo.append(f"FAIL: local-only files tracked {leaked[:5]}")
    big = [(t, (ROOT / t).stat().st_size) for t in tracked
           if t.startswith(("data/", "models/")) and (ROOT / t).exists() and (ROOT / t).stat().st_size > 5 * 1024 * 1024]
    if big:
        repo.append(f"FAIL: files > 5 MB {big}")
    hits = []
    for t in tracked:
        p = ROOT / t
        if p.suffix in {".png", ".jpg", ".gpkg", ".joblib", ".pbf"} or not p.exists() or p.stat().st_size > 3_000_000:
            continue
        try:
            if SECRET.search(p.read_text(encoding="utf-8", errors="ignore")):
                hits.append(t)
        except OSError:
            pass
    if hits:
        repo.append(f"FAIL: possible secrets in {hits}")
    fails += repo

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    total = sum(r[1] for r in rows)
    st_all = Counter()
    for r in rows:
        st_all.update(r[2])
    lines = [f"# Data audit — {'PASS' if not fails else 'FAIL'}", "",
             f"Generated {now} by `scripts/audit_data.py` over every layer the API serves ({len(rows)} layers, "
             f"{total:,} features). Status mix: " + ", ".join(f"{k} {v:,}" for k, v in st_all.most_common()) + ".", "",
             "| Layer | Features | data_status | source_id | Result |", "|---|---|---|---|---|"]
    lines += [f"| {n} | {c:,} | {', '.join(f'{k} {v}' for k, v in s.items())} | {', '.join(src)} | {res} |"
              for n, c, s, src, res in rows]
    lines += ["", "## Repository checks",
              f"- `.env` tracked: {'yes — FAIL' if any(r.startswith('FAIL: .env') for r in repo) else 'no'}",
              f"- Local-only (Claude Code) files tracked: {'yes — FAIL' if leaked else 'no'}",
              f"- Committed data/model files > 5 MB: {big or 'none'}",
              f"- Possible secrets in tracked text files: {hits or 'none'}", "",
              "## Rules checked",
              "- Every feature has `asset_id` (unique within and across layers), a valid `data_status`, and a `source_id` "
              "registered in `docs/DATA_SOURCES.md`.",
              f"- Layers that must be labelled simulated: {', '.join(sorted(MUST_BE_SIMULATED))}.",
              "- Every simulated or modelled feature states its assumptions.", ""]
    if fails:
        lines += ["## Failures", *[f"- {f}" for f in fails], ""]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"audit {'PASS' if not fails else 'FAIL'}: {len(rows)} layers, {total:,} features → {OUT.relative_to(ROOT)}")
    for f in fails:
        print("  ", f)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
