# tools/repo.py — файловые операции репозитория
from __future__ import annotations

from pathlib import Path


class RepoOps:
    def __init__(self, root: str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def write_file(self, rel_path: str, content: str) -> None:
        p = self.root / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    def ensure_gitkeep(self, rel_dir: str) -> None:
        d = self.root / rel_dir
        d.mkdir(parents=True, exist_ok=True)
        (d / ".gitkeep").write_text("", encoding="utf-8")
