"""P04: create/update the Hugging Face Space (Docker SDK) from deploy/hf-space/.

Needs HF_TOKEN (write) and HF_SPACE (<user>/<name>) in the environment or .env. Run via scripts/deploy.ps1.
Usage: python scripts/deploy_space.py --cors "https://<app>.vercel.app,http://localhost:5173"
"""
import argparse
import os
from pathlib import Path

from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parents[1]


def env(key: str) -> str:
    if os.environ.get(key):
        return os.environ[key]
    dotenv = ROOT / ".env"
    if dotenv.exists():
        for line in dotenv.read_text(encoding="utf-8").splitlines():
            k, _, v = line.partition("=")
            if k.strip() == key:
                return v.split("#", 1)[0].strip()
    raise SystemExit(f"{key} missing — set it in .env")


def space_url(repo_id: str) -> str:
    return "https://" + repo_id.lower().replace("/", "-").replace("_", "-").replace(".", "-") + ".hf.space"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cors", default="", help="comma-separated allowed origins")
    args = ap.parse_args()
    token, repo = env("HF_TOKEN"), env("HF_SPACE")
    folder = ROOT / "deploy" / "hf-space"
    if not (folder / "Dockerfile").exists():
        raise SystemExit("deploy/hf-space missing — run scripts/build_space.ps1")

    api = HfApi(token=token)
    api.create_repo(repo, repo_type="space", space_sdk="docker", exist_ok=True)
    if args.cors:
        api.add_space_variable(repo, "CORS_ORIGINS", args.cors, description="Allowed browser origins")
    info = api.upload_folder(repo_id=repo, repo_type="space", folder_path=folder,
                             commit_message="Hyperborea API deploy", delete_patterns=["*"])
    print("uploaded:", info.commit_url)
    print("space:   ", f"https://huggingface.co/spaces/{repo}")
    print("api:     ", space_url(repo) + "/api/health")


if __name__ == "__main__":
    main()
