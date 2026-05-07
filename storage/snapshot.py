"""
Storage — Gestion des snapshots JSON pour la détection de changements
"""

import json
import os
from datetime import datetime
from pathlib import Path

STORAGE_DIR = Path(__file__).parent.parent / "storage" / "snapshots"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def snapshot_path(competitor_slug: str) -> Path:
    return STORAGE_DIR / f"{competitor_slug}.json"


def load_snapshot(competitor_slug: str) -> dict | None:
    path = snapshot_path(competitor_slug)
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def save_snapshot(competitor_slug: str, data: dict):
    data["_saved_at"] = datetime.now().isoformat()
    with open(snapshot_path(competitor_slug), "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def slugify(name: str) -> str:
    return name.lower().strip().replace(" ", "_").replace("/", "-")[:40]
