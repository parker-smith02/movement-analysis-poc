"""Download model weights used by the lab into lab/models/ (gitignored).

Idempotent: skips files that already exist. Re-run after a fresh clone.
"""

from pathlib import Path
from urllib.request import urlretrieve

MODELS_DIR = Path(__file__).parent / "models"

MODELS = {
    "pose_landmarker_heavy.task": (
        "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
        "pose_landmarker_heavy/float16/latest/pose_landmarker_heavy.task"
    ),
}


def main() -> None:
    MODELS_DIR.mkdir(exist_ok=True)
    for filename, url in MODELS.items():
        dest = MODELS_DIR / filename
        if dest.exists():
            print(f"already present: {dest}")
            continue
        print(f"downloading {filename} ...")
        urlretrieve(url, dest)
        print(f"  -> {dest} ({dest.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
