from pathlib import Path

from fastapi.testclient import TestClient

from src.mas.server import app


def test_health_ok():
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert data.get("service") == "devforge-mas"
    assert "ts" in data


def test_contracts_stub_or_file(tmp_path: Path, monkeypatch):
    """
    Проверяем, что /contracts отвечает и с файлом, и без него.
    """
    client = TestClient(app)

    # Без файла — должна прийти заглушка (ok=True, raw=None)
    r1 = client.get("/contracts")
    assert r1.status_code == 200
    data1 = r1.json()
    assert data1.get("ok") is True
    assert "raw" in data1

    # С файлом — вернётся содержимое в "raw"
    ws = tmp_path / "workspace" / "contracts"
    ws.mkdir(parents=True)
    contracts = ws / "CONTRACTS.json"
    contracts.write_text('{"version":"0.0.1","endpoints":[],"schemas":{}}', encoding="utf-8")

    # Подменяем рабочую директорию на tmp_path, чтобы сервер читал наш файл
    # В api.py путь рассчитывается как Path("workspace") относительно CWD.
    monkeypatch.chdir(tmp_path)

    r2 = client.get("/contracts")
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2.get("ok") is True
    assert data2.get("raw") is not None
    assert '"version":"0.0.1"' in data2["raw"]
