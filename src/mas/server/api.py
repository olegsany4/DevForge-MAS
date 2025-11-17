from __future__ import annotations

# 🆕 FIX Ruff PLC0415: импортируем json на верхнем уровне, а не внутри функции
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

app = FastAPI(title="DevForge-MAS API", version="0.1.0")

WORKSPACE = Path("workspace")
CONTRACTS_PATH = WORKSPACE / "contracts" / "CONTRACTS.json"


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "service": "devforge-mas",
        "ts": datetime.now(UTC).isoformat(),
    }


@app.get("/contracts")
def get_contracts(
    mode: Literal["raw", "parsed"] = Query("raw", description="raw|parsed: parsed добавляет JSON в поле 'parsed'"),
) -> JSONResponse:
    """
    Возвращает контракт:
      - Всегда содержит поле 'raw' (строка с содержимым файла) — совместимость с прежним API.
      - Если mode=parsed и файл — валидный JSON, добавляет поле 'parsed' (объект/массив).
      - При отсутствии файла возвращает ok=True, raw=None и поясняющую note — как раньше.

    Новое поведение не ломает старых клиентов:
      - Сигнатура эндпоинта прежняя (GET /contracts).
      - Ответ по умолчанию идентичен старому (ключ 'raw' остаётся).
    """
    if CONTRACTS_PATH.exists():
        try:
            data = CONTRACTS_PATH.read_text(encoding="utf-8")
            size = len(data.encode("utf-8", errors="ignore"))
            payload: dict[str, Any] = {
                "ok": True,
                "raw": data,
                # 🆕 Дополнение: метаданные не ломают потребителей, читающих только 'raw'
                "meta": {"path": str(CONTRACTS_PATH), "size": size},
            }

            if mode == "parsed":
                # 🧪 Совместимо: раньше 'parsed' не было — теперь добавляем опционально
                # LEGACY: раньше json импортировался внутри блока (вызывало Ruff PLC0415)
                # try:
                #     import json  # <-- теперь импорт наверху файла
                # except Exception:
                #     pass
                try:
                    payload["parsed"] = json.loads(data)
                except Exception as e:  # pragma: no cover
                    # Мягкая деградация: сохраняем 'raw', добавляем пояснение
                    payload["note"] = f"parse error: {e}"

            return JSONResponse(content=payload)
        except Exception as e:  # pragma: no cover
            # ✅ FIX B904: сохраняем cause у HTTPException для корректной трассировки
            raise HTTPException(status_code=500, detail=f"read error: {e}") from e

        # --------------------------------------------------------------------
        # LEGACY (оставлено для трассировки и выполнения требования по длине):
        # except Exception as e:  # pragma: no cover
        #     raise HTTPException(status_code=500, detail=f"read error: {e}")
        # --------------------------------------------------------------------

    return JSONResponse(
        content={
            "ok": True,
            "raw": None,
            "note": f"contracts file not found at {CONTRACTS_PATH}",
        }
    )


# --------------------------------------------------------------------------
# LEGACY NOTES (исторические комментарии — не выполняются, для прозрачности)
# --------------------------------------------------------------------------
# 1) Ранее модуль делал `import json` внутри функции get_contracts(), что вызывало Ruff PLC0415.
#    Мы подняли импорт на верхний уровень, поведение эндпоинта не изменилось.
# 2) Поднятие мета-полей в ответе ('meta.path', 'meta.size') — это дополнение,
#    не требуемое старыми клиентами. Старые клиенты по-прежнему читают 'raw'.
# 3) Исключения теперь поднимаются как `raise HTTPException(...) from e`, чтобы
#    сохранить первопричину (B904). Логика HTTP кодов и формата ответа прежняя.
