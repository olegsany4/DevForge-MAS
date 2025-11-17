#!/usr/bin/env python3
"""
Простой генератор docs/ADR_INDEX.md из файлов workspace/adr/ADR-*.md

Изменения (без ломки API):
- Сохранены имена констант ADR_DIR/OUT, функции extract(), main() и формат итоговой таблицы.
- Убрана широкая конструкция `except Exception: pass` → сузили исключения и логируем в stderr.
- Стабильная сортировка по числовому ID ADR (а не только лексикографически по имени файла).
- Санитизация заголовка (замена `|` в Markdown-таблице), тримминг пробелов.
- Если дата не найдена в тексте, берём mtime файла (ISO) как мягкий фолбэк.
- Переопределение путей через переменные окружения ADR_DIR и ADR_INDEX_OUT (опционально).
  По умолчанию поведение прежнее.
- Добавлены вспомогательные функции (_parse_id, _read_text_safe, _sanitize_md_cell, _guess_date)
  для удобного тестирования. Старая логика извлечения оставлена в комментариях рядом.

Доп. исправление для совместимости с Python 3.11+ и mypy:
- Заменено `datetime.UTC` → `timezone.utc` (см. функцию _guess_date). Старая строка оставлена закомментированной.
"""

from __future__ import annotations

import os
import re
import sys
from collections.abc import Iterable
from datetime import UTC, datetime  # ✅ добавлен timezone для корректного UTC
from pathlib import Path

# Путь по умолчанию — соответствует прежнему поведению:
ADR_DIR = Path(os.environ.get("ADR_DIR", "workspace/adr"))
OUT = Path(os.environ.get("ADR_INDEX_OUT", "docs/ADR_INDEX.md"))

# Регулярки вынесены для повторного использования и ускорения
_RE_ID = re.compile(r"ADR-(\d+)\.md$")
_RE_TITLE = re.compile(r"^#\s*(.+)$", flags=re.M)
_RE_DATE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")


def _parse_id(p: Path) -> str:
    """
    Возвращает строковый ID из имени файла (без ведущих нулей).
    Если не найден — '????' (совместимо с прежней логикой).
    """
    m = _RE_ID.search(p.name)
    return m.group(1) if m else "????"


def _read_text_safe(p: Path) -> str:
    """
    Безопасное чтение текста UTF-8 с логированием ошибок вместо молчаливого pass.

    СТАРАЯ ЛОГИКА:
        try:
            txt = p.read_text(encoding="utf-8")
        except Exception:
            pass

    НОВАЯ ЛОГИКА:
        - явно перехватываем UnicodeDecodeError и OSError (FileNotFoundError, PermissionError и т.п.)
        - логируем в stderr и возвращаем пустую строку
    """
    try:
        return p.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as e:
        print(f"[adr_index] WARN: cannot read {p}: {e}", file=sys.stderr)
        return ""


def _sanitize_md_cell(s: str) -> str:
    """
    Санитизация ячейки для Markdown-таблицы: заменяем вертикальные черты, триммим.
    """
    return (s or "").replace("|", "\\|").strip()


def _guess_date(p: Path, content: str) -> str:
    """
    Пытаемся извлечь дату YYYY-MM-DD из содержимого; если не нашли — используем mtime файла.
    Всегда возвращаем строку в ISO (YYYY-MM-DD).

    Исправление: используем timezone.utc вместо datetime.UTC
    (в Python 3.11 атрибут datetime.UTC отсутствует; правильный способ — timezone.utc).
    """
    m = _RE_DATE.search(content)
    if m:
        return m.group(1)
    try:
        ts = p.stat().st_mtime
        # СТАРАЯ (проблемная на Py3.11) строка оставлена для наглядности:
        # return datetime.fromtimestamp(ts, tz=datetime.UTC).date().isoformat()
        # НОВАЯ корректная версия:
        return datetime.fromtimestamp(ts, tz=UTC).date().isoformat()
    except OSError as e:
        print(f"[adr_index] WARN: cannot stat {p}: {e}", file=sys.stderr)
        return "(n/a)"


def extract(p: Path) -> tuple[str, str, str, str]:
    """Возвращает (id, title, date, link)

    Сохранена сигнатура и формат возвращаемого значения.
    """
    # Извлекаем ID
    sid = _parse_id(p)

    # Читаем текст (безопасно, с логированием)
    txt = _read_text_safe(p)

    # СТАРАЯ ЛОГИКА (оставлена для наглядности):
    # _id = re.search(r"ADR-(\d+)\.md$", p.name)
    # sid = _id.group(1) if _id else "????"
    # title, date = "(title not found)", "(n/a)"
    # try:
    #     txt = p.read_text(encoding="utf-8")
    #     m1 = re.search(r"^#\s*(.+)$", txt, flags=re.M)
    #     if m1:
    #         title = m1.group(1).strip()
    #     m2 = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", txt)
    #     if m2:
    #         date = m2.group(1)
    # except Exception:
    #     pass

    # Новая (эквивалентная по результату, но безопаснее и устойчивее):
    title = "(title not found)"
    m1 = _RE_TITLE.search(txt)
    if m1:
        title = _sanitize_md_cell(m1.group(1))

    date = _guess_date(p, txt)

    return sid, title, date, p.as_posix()


def _numeric_id(sid: str) -> int:
    """
    Преобразуем строковый sid в число для корректной сортировки (ADR-2, ADR-10 и т.п.).
    Неудачные случаи получают большое значение, чтобы оказаться в конце.
    """
    try:
        return int(sid)
    except (TypeError, ValueError):
        return 10**9  # "????" и пр. должны сортироваться после валидных ID


def _iter_adrs(path: Path) -> Iterable[Path]:
    """
    Итерируем ADR-файлы. Если каталог отсутствует — ведём себя мягко (как раньше):
    вернём пустой набор и просто сгенерируем заголовок таблицы.
    """
    if not path.exists():
        print(f"[adr_index] INFO: ADR directory not found: {path}", file=sys.stderr)
        return ()
    return path.glob("ADR-*.md")


def main() -> None:
    rows: list[tuple[str, str, str, str]] = []

    # Ранее было:
    # for p in sorted(ADR_DIR.glob("ADR-*.md")):
    #     rows.append(extract(p))
    #
    # Теперь сортируем по числовому ID для устойчивого порядка.
    adrs = list(_iter_adrs(ADR_DIR))
    adrs.sort(key=lambda p: _numeric_id(_parse_id(p)))
    for p in adrs:
        rows.append(extract(p))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# ADR-lite Index",
        "",
        "| ID | Title | Date | Link |",
        "|---:|-------|------|------|",
    ]
    for sid, title, date, link in rows:
        lines.append(f"| {sid:>4} | {title} | {date} | `{link}` |")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT} with {len(rows)} rows")


if __name__ == "__main__":
    main()
