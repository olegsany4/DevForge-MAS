# tests/test_api_contracts.py
from __future__ import annotations

import json
import sys
from importlib import import_module
from pathlib import Path

import httpx
import pytest
from httpx import ASGITransport


def _load_app():
    repo_root = Path(__file__).resolve().parents[1]
    src_path = repo_root / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    mod = import_module("mas.server.api")
    return mod.app  # прямой доступ ок


@pytest.fixture
def anyio_backend():
    # Явно просим asyncio, чтобы не требовался trio
    return "asyncio"


@pytest.mark.anyio
async def test_health_ok():
    app = _load_app()
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, dict)
        # сервер сейчас возвращает {"ok": true, ...}; допускаем "status" или "ok"
        assert ("status" in data) or (data.get("ok") is True)


@pytest.mark.anyio
async def test_contracts_shape():
    app = _load_app()
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/contracts")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, dict)

        # Два допустимых формата:
        # 1) Прямо словарь с "endpoints"/"schemas"
        # 2) {"ok": true, "raw": "<json>"} — парсим raw
        if "endpoints" in data and "schemas" in data:
            payload = data
        else:
            raw = data.get("raw")
            assert isinstance(raw, str) and raw.strip().startswith("{")
            payload = json.loads(raw)

        assert "endpoints" in payload and "schemas" in payload
        assert isinstance(payload["endpoints"], list | tuple)
        assert isinstance(payload["schemas"], (list | dict))
        if payload["endpoints"]:
            sample = payload["endpoints"][0]
            assert isinstance(sample, dict)
            for k in ("method", "path"):
                assert k in sample
