# tests_fe/test_build_smoke.py
# Простая проверка, что фронтенд собирается и в dist/ появляется index.html.
# По умолчанию ТЕСТ ПРОПУСКАЕТСЯ. Включить через переменную окружения FE_SMOKE=1.
#
# Пример:
#   FE_SMOKE=1 pytest -q tests_fe/test_build_smoke.py

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


def _run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, check=False, capture_output=True, text=True)


@pytest.mark.skipif(os.environ.get("FE_SMOKE", "0") != "1", reason="set FE_SMOKE=1 to enable")
def test_vite_build_produces_dist_index_html(tmp_path: Path):
    repo = Path(__file__).resolve().parents[1]
    fe_dir = repo / "workspace" / "frontend"

    assert fe_dir.exists(), f"frontend not found: {fe_dir}"

    # npm ci предпочтительнее, если есть package-lock.json
    pkg_lock = fe_dir / "package-lock.json"
    if pkg_lock.exists():
        install = _run(["npm", "ci"], cwd=fe_dir)
    else:
        install = _run(["npm", "install"], cwd=fe_dir)

    assert install.returncode == 0, f"npm install failed:\n{install.stdout}\n{install.stderr}"

    build = _run(["npm", "run", "build"], cwd=fe_dir)
    assert build.returncode == 0, f"npm run build failed:\n{build.stdout}\n{build.stderr}"

    dist = fe_dir / "dist"
    index_html = dist / "index.html"
    assert dist.exists(), f"dist not found: {dist}"
    assert index_html.exists(), f"index.html not found in dist: {index_html}"

    # Небольшая содержательная проверка
    text = index_html.read_text(encoding="utf-8", errors="ignore")
    assert "<!doctype html" in text.lower()
