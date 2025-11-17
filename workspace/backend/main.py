from __future__ import annotations

# Новый импорт для работы с путями к фронтенду.
from pathlib import Path

from fastapi import FastAPI

# Новые импорты для раздачи HTML и статики (фронтенд).
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Приложение FastAPI. Название сохранено, чтобы не ломать интеграции.
app = FastAPI(title="DevForge-MAS Demo API")

# Базовая директория для поиска фронтенда.
# __file__ -> .../workspace/backend/main.py
# parent -> .../workspace/backend
# parent.parent -> .../workspace
BASE_DIR = Path(__file__).resolve().parent.parent

# Путь к Vite-сборке фронтенда (workspace/frontend/dist).
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"


# Модель входных данных для /items.
# Логика и сигнатура сохранены без изменений.
class ItemIn(BaseModel):
    name: str
    price: float | None = None
    tags: list[str] | None = None


# "База данных" в памяти (как и было).
DB: dict[str, dict] = {}


# ОРИГИНАЛЬНЫЙ ЭНДПОИНТ: сохранён без изменений.
@app.post("/items")
def create_item(item: ItemIn):
    """
    Создание/обновление Item в in-memory DB.

    СТАРАЯ ЛОГИКА (для референса, не менялась):

    def create_item(item: ItemIn):
        DB[item.name] = item.model_dump()
        return {"ok": True, "item": DB[item.name]}
    """
    # Логика не менялась — оставлена строго такой же.
    DB[item.name] = item.model_dump()
    return {"ok": True, "item": DB[item.name]}


# ОРИГИНАЛЬНЫЙ ЭНДПОИНТ: сохранён без изменений.
@app.get("/items/{name}")
def get_item(name: str):
    """
    Получение Item по имени из in-memory DB.

    СТАРАЯ ЛОГИКА (для референса, не менялась):

    def get_item(name: str):
        return DB.get(name, {})
    """
    # Логика не менялась — оставлена строго такой же.
    return DB.get(name, {})


# НОВЫЙ ФУНКЦИОНАЛ: health-check эндпоинт для мониторинга.
@app.get("/health")
async def health() -> dict[str, str]:
    """
    Простой health-check для Docker/мониторинга/CI.

    Обратная совместимость:
    - Не переопределяет существующие маршруты.
    - Не меняет поведение /items.
    """
    return {"status": "ok"}


# НОВЫЙ ФУНКЦИОНАЛ: раздача фронтенда из workspace/frontend/dist.
# Реализовано через условие, чтобы не ломать среду без собранного фронтенда.
if FRONTEND_DIST.exists():
    # Если есть поддиректория assets, монтируем её на /assets.
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        # StaticFiles позволяет раздавать JS/CSS и прочий статик.
        app.mount(
            "/assets",
            StaticFiles(directory=assets_dir, html=False),
            name="assets",
        )

    @app.get("/", response_class=HTMLResponse)
    async def frontend_index() -> str:
        """
        Отдаём index.html Vite-фронтенда как корневую страницу.

        Обратная совместимость:
        - Ранее / не был определён (давал 404), теперь возвращаем UI.
        - Никакие существующие API-роуты не переопределены.
        """
        index_file = FRONTEND_DIST / "index.html"
        # Если вдруг файла нет, будет исключение, что упростит диагностику
        # при некорректной сборке фронтенда.
        return index_file.read_text(encoding="utf-8")


# Если FRONTEND_DIST не существует, приложение ведёт себя
# как раньше: /items* работают, /docs работает, / даёт 404.
# Это сохраняет поведение старой версии там, где нет фронтенда.
