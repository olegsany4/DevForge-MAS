# [PATCH] Корневой пакет для CLI: расширяем путь поиска подмодулей на src/mas
from __future__ import annotations

from pathlib import Path

# Разрешаем подмодули пакета mas из каталога src/mas
_pkg_dir = Path(__file__).resolve().parent  # .../mas
_src_mas = _pkg_dir.parent / "src" / "mas"  # .../src/mas
try:
    # Если src/mas существует, добавим его в __path__ для текущего пакета
    if _src_mas.exists():
        __path__.append(str(_src_mas))  # type: ignore[name-defined]
except Exception:
    # Никогда не падаем из-за расширения пути
    pass

# Сохраняем прежнее поведение (если было): экспорт пустого __all__
__all__: list[str] = []
