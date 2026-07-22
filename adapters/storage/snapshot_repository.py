"""Adapter de stockage — implémente SnapshotRepository via des fichiers JSON."""

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from domain.models import CompetitorSnapshot

STORAGE_DIR = Path(__file__).parent.parent.parent / "storage" / "snapshots"


def slugify(name: str) -> str:
    return name.lower().strip().replace(" ", "_").replace("/", "-")[:40]


class JsonSnapshotRepository:
    def __init__(self, storage_dir: Path = STORAGE_DIR) -> None:
        self._storage_dir = storage_dir
        self._storage_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, competitor_name: str) -> Path:
        return self._storage_dir / f"{slugify(competitor_name)}.json"

    def load(self, competitor_name: str) -> CompetitorSnapshot | None:
        path = self._path(competitor_name)
        if not path.exists():
            return None
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return CompetitorSnapshot(
            name=data.get("name", competitor_name),
            website=data.get("website"),
            homepage=data.get("homepage"),
            pricing=data.get("pricing"),
            blog_titles=data.get("blog_titles", []),
            linkedin_posts=data.get("linkedin_posts", []),
            twitter_posts=data.get("twitter_posts", []),
            saved_at=data.get("_saved_at"),
        )

    def save(self, competitor_name: str, snapshot: CompetitorSnapshot) -> None:
        data = asdict(snapshot)
        data.pop("saved_at", None)
        data["_saved_at"] = datetime.now().isoformat()
        with open(self._path(competitor_name), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
