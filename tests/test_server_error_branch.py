from pathlib import Path

from fastapi.testclient import TestClient

from src.mas.server import app


def test_contracts_read_error(monkeypatch, tmp_path):
    client = TestClient(app)

    # Готовим существующий файл, но чтение будет «падать»
    ws = tmp_path / "workspace" / "contracts"
    ws.mkdir(parents=True)
    (ws / "CONTRACTS.json").write_text("{}", encoding="utf-8")

    # Сместим CWD, чтобы сервер смотрел в наш tmp workspace
    monkeypatch.chdir(tmp_path)

    # Ломаем Path.read_text на время теста
    def boom_read_text(self, encoding="utf-8"):
        raise OSError("boom")

    monkeypatch.setattr(Path, "read_text", boom_read_text, raising=True)

    r = client.get("/contracts")
    # Ожидаем 500 от нашего HTTPException
    assert r.status_code == 500
    assert "read error" in r.text
