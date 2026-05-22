from pathlib import Path
from huggingface_hub import snapshot_download

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "models"
MODELS.mkdir(exist_ok=True)

MODELS_TO_DOWNLOAD = {
    "small": "Systran/faster-whisper-small",
    "medium": "Systran/faster-whisper-medium",
    # Large is heavy. The app can download it on demand.
    # "large-v3": "Systran/faster-whisper-large-v3",
}

for name, repo in MODELS_TO_DOWNLOAD.items():
    target = MODELS / f"faster-whisper-{name}"
    if target.exists() and any(target.iterdir()):
        print(f"Already exists: {target}")
        continue
    print(f"Downloading {repo} -> {target}")
    snapshot_download(repo_id=repo, local_dir=str(target), local_dir_use_symlinks=False)
    print(f"Done: {name}")

print("All selected models are ready.")
