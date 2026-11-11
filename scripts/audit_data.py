"""Data audit → local/cache/DATA_AUDIT.md (exit 1 on any failure).

Checks every served layer (GPKGs + curated/synthetic GeoJSON, exactly what the API loads):
asset_id present + unique · data_status valid · source_id registered in docs/DATA.md · simulated layers are
labelled simulated/curated · simulated/modelled features state assumptions. Repo: .env + local-only files untracked,
no obvious secrets tracked, committed data/model files < 5 MB.
Run:  python scripts/audit_data.py
"""
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.core import regions as R  # noqa: E402
from backend.app.core.provenance import DataStatus  # noqa: E402
from backend.app.services.layer_store import LayerStore  # noqa: E402

OUT = ROOT / "local" / "cache" / "DATA_AUDIT.md"  # report stays local (git-ignored)
MUST_BE_SIMULATED = {"drains", "drain_nodes", "catchments", "transformers", "feeders", "water_quality"}
SECRET = re.compile(r"(hf_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|"
                    r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----)")


def main() -> int:
    reg = ROOT / "docs" / "DATA.md"  # source register: one "### <source_id> — …" heading per source
    sources = set(re.findall(r"^### (\S+)", reg.read_text(encoding="utf-8"), re.M)) if reg.exists() else None
    if sources is None:
        print("note: docs/DATA.md not found — source_id registration not checked")
    valid = {s.value for s in DataStatus}
    rows, fails = [], []
    ready = [rid for rid in R.registry() if R.is_ready(rid)]
    for rid in ready:  # P16: every region with data, each checked on its own
        tok = R.set_current(rid)
        try:
            _audit_region(rid, LayerStore.load(), sources, valid, rows, fails)
        finally:
            R.reset(tok)
    _repo_and_report(rows, fails, ready)
    return 1 if fails else 0


def _audit_region(rid, store, sources, valid, rows, fails) -> None:
    all_ids = Counter()
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
        if sources is not None and srcs - sources:
            probs.append(f"unregistered source_id {sorted(srcs - sources)}")
        if name in MUST_BE_SIMULATED and set(status) - {"simulated", "curated"}:
            probs.append(f"must be simulated, has {dict(status)}")
        needs = g[g.data_status.isin(["simulated", "modelled"])]
        if len(needs) and (needs.assumptions.fillna("").str.len() == 0).any():
            probs.append("simulated/modelled features without assumptions")
        all_ids.update(g.asset_id)
        rows.append((f"{rid} · {name}", n, dict(status), sorted(srcs), "PASS" if not probs else "FAIL: " + "; ".join(probs)))
        fails += [f"{rid} · {name}: {p}" for p in probs]
    dup_across = [a for a, c in all_ids.items() if c > 1]
    if dup_across:
        fails.append(f"{rid}: asset_id shared across layers: {dup_across[:5]}")


def _repo_and_report(rows, fails, ready) -> None:
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.splitlines()
    repo = []
    if any(t == ".env" or t.endswith("/.env") for t in tracked):
        repo.append("FAIL: .env is tracked")
    # 2026-11-07: Claude workflow files are tracked on purpose (private repo, user decision); large files go via LFS
    lfs = set(subprocess.run(["git", "lfs", "ls-files", "-n"], cwd=ROOT, capture_output=True, text=True).stdout.splitlines())
    big = [(t, (ROOT / t).stat().st_size) for t in tracked
           if t not in lfs and (ROOT / t).exists() and (ROOT / t).stat().st_size > 5 * 1024 * 1024]
    if big:
        repo.append(f"FAIL: non-LFS files > 5 MB {big}")
    hits = []
    for t in tracked:
        p = ROOT / t
        if t in lfs or p.suffix in {".png", ".jpg", ".gpkg", ".joblib", ".pbf"} or not p.exists() or p.stat().st_size > 3_000_000:
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
             f"Generated {now} by `scripts/audit_data.py` over every layer the API serves in {len(ready)} region(s) — {", ".join(ready)} ({len(rows)} layers, "
             f"{total:,} features). Status mix: " + ", ".join(f"{k} {v:,}" for k, v in st_all.most_common()) + ".", "",
             "| Region · layer | Features | data_status | source_id | Result |", "|---|---|---|---|---|"]
    lines += [f"| {n} | {c:,} | {', '.join(f'{k} {v}' for k, v in s.items())} | {', '.join(src)} | {res} |"
              for n, c, s, src, res in rows]
    lines += ["", "## Repository checks",
              f"- `.env` tracked: {'yes — FAIL' if any(r.startswith('FAIL: .env') for r in repo) else 'no'}",
              f"- Files in Git LFS: {len(lfs)}",
              f"- Non-LFS files > 5 MB: {big or 'none'}",
              f"- Possible secrets in tracked text files: {hits or 'none'}", "",
              "## Rules checked",
              "- Every feature has `asset_id` (unique within and across layers), a valid `data_status`, and a `source_id` "
              "registered in `docs/DATA.md`.",
              f"- Layers that must be labelled simulated: {', '.join(sorted(MUST_BE_SIMULATED))}.",
              "- Every simulated or modelled feature states its assumptions.", ""]
    if fails:
        lines += ["## Failures", *[f"- {f}" for f in fails], ""]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"audit {'PASS' if not fails else 'FAIL'}: {len(ready)} region(s), {len(rows)} layers, {total:,} features -> "
          f"{OUT.relative_to(ROOT)}")
    for f in fails:
        print("  ", f)


if __name__ == "__main__":
    sys.exit(main())
