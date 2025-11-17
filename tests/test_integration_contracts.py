# tests/test_integration_contracts.py
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WS = ROOT / "workspace"


def _load(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def test_contracts_endpoints_have_method_and_path():
    contracts = _load(WS / "CONTRACTS.json")
    eps = contracts.get("endpoints", [])
    assert eps, "No endpoints in CONTRACTS.json"
    for ep in eps:
        assert "method" in ep and isinstance(ep["method"], str) and ep["method"], "endpoint.method required"
        assert "path" in ep and isinstance(ep["path"], str) and ep["path"].startswith("/"), "endpoint.path must start with '/'"


def test_schemas_are_named_and_unique():
    contracts = _load(WS / "CONTRACTS.json")
    schemas = contracts.get("schemas", [])
    names = [s.get("name") for s in schemas if isinstance(s, dict)]
    assert all(names), "Every schema must have a non-empty 'name'"
    assert len(names) == len(set(names)), "Schema names must be unique"


def test_adr_registry_has_unique_ids_if_present():
    adr_dir = WS / "ADR"
    if not (adr_dir.exists() and adr_dir.is_dir()):
        return  # допустимо отсутствие каталога в ранней инициализации
    ids = []
    for p in adr_dir.glob("ADR-*.md"):
        ids.append(p.stem)  # ADR-0001 ..
    assert len(ids) == len(set(ids)), "ADR IDs must be unique"
