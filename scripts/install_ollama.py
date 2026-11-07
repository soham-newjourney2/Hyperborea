"""P14: install Ollama portable (Windows, CUDA build) into local/tools/ollama — no global install (D-05).

Run:  python scripts/install_ollama.py [version]   (default: latest GitHub release)
Then: . .\\scripts\\env.ps1 ; ollama serve   (models go to local/ollama/models via OLLAMA_MODELS)
"""
import json
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "local" / "tools" / "ollama"
TMP = ROOT / "local" / "cache" / "ollama-windows-amd64.zip"
UA = {"User-Agent": "Hyperborea/0.1 (local install script)"}


def main(version: str | None = None) -> None:
    api = f"https://api.github.com/repos/ollama/ollama/releases/{'tags/' + version if version else 'latest'}"
    rel = json.load(urllib.request.urlopen(urllib.request.Request(api, headers=UA), timeout=60))
    asset = next(a for a in rel["assets"] if a["name"] == "ollama-windows-amd64.zip")
    print(f"Ollama {rel['tag_name']}: {asset['size'] / 1e6:.0f} MB → {TMP}", flush=True)
    TMP.parent.mkdir(parents=True, exist_ok=True)
    # Resumable download: HTTP Range from the bytes already on disk, retried on timeouts / resets.
    for attempt in range(12):
        done = TMP.stat().st_size if TMP.exists() else 0
        if done >= asset["size"]:
            break
        try:
            req = urllib.request.Request(asset["browser_download_url"], headers={**UA, "Range": f"bytes={done}-"})
            with urllib.request.urlopen(req, timeout=120) as r, TMP.open("ab") as f:
                while chunk := r.read(1 << 22):
                    f.write(chunk)
                    done += len(chunk)
                    if done % (200 << 20) < (1 << 22):
                        print(f"  {done / 1e6:.0f} MB", flush=True)
        except (TimeoutError, OSError) as e:
            print(f"  interrupted at {done / 1e6:.0f} MB ({type(e).__name__}); resuming (attempt {attempt + 2})", flush=True)
    if TMP.stat().st_size != asset["size"]:
        raise SystemExit("download incomplete — rerun to resume")
    DEST.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(TMP) as z:
        z.extractall(DEST)
    (DEST / "VERSION.txt").write_text(rel["tag_name"], encoding="utf-8")
    exe = next(DEST.rglob("ollama.exe"), None)
    print("installed:", exe, flush=True)
    TMP.unlink()


if __name__ == "__main__":
    main(*sys.argv[1:])
