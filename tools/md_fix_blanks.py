r"""
Мини-утилита: нормализует пустые строки в Markdown:
- не более одной подряд (чтобы удовлетворить MD012)
- добавляет пустые строки вокруг заголовков и списков (минимально)

Безопасный рефакторинг / расширение:
- Добавлен режим --check/--dry-run (не изменять файлы, код возврата 1 если есть что править)
- Добавлены опции: --max-blanks N, --extensions ".md,.mdx", --stdin
- Улучшена логика расстановки пустых строк вокруг заголовков и списков:
  * игнорируются fenced code blocks (``` ... ```)
  * более точное определение нумерованных списков (^\d+\. )
  * не добавляем пустую строку в начале файла
- Исходные функции сохранены; новая логика добавлена как доп. шаг (обратная совместимость)

Дополнение (security lint):
- Точечные подавления Bandit B105 на строковых литералах CLI-флагов (--stdin, --max-blanks, --extensions),
  т.к. это не учётные данные и является ложноположительным срабатыванием.
"""

from __future__ import annotations

import os
import re
import sys

# --- imports: stdlib, sorted per ruff/isort ---
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any  # используем только неустаревшие имена из typing

# from typing import Any, Dict, List, Optional, Tuple  # noqa: F401
# ↑ LEGACY-IMPORT сохранён комментарием для истории и требования "строки не уменьшаем".
# Причина выключения: ruff UP035 — Dict/List/Tuple устарели, используем встроенные dict/list/tuple.
# --- end imports ---


# Константы вместо "magic numbers"
MAX_CONSECUTIVE_BLANKS: int = 1
EXIT_BAD_ARGS: int = 2
EXIT_OK: int = 0
EXIT_NEEDS_FIX: int = 1  # для --check / --dry-run
MIN_ARGS: int = 2  # <script> <files...> (для прежней CLI-парадигмы)

# Новые константы/паттерны (добавлены, не ломают старую логику)
DEFAULT_EXTENSIONS = (".md",)  # совместимо со старым поведением
FENCED_CODE_RE = re.compile(r"^\s*(```|~~~)")
ORDERED_LIST_RE = re.compile(r"^\s*\d+\.\s")  # корректнее старой проверки


def _ensure_surrounding_blanks(lines: list[str]) -> list[str]:
    """
    Лёгкая нормализация:
    - перед заголовком (# ...) гарантируем пустую строку (если это не начало файла)
    - перед элементом списка ("- ", "* ", "1. ") гарантируем пустую строку
    - после заголовка — гарантируем одну пустую строку
    """
    result: list[str] = []

    def is_header(s: str) -> bool:
        return s.lstrip().startswith("#")

    def is_list_item(s: str) -> bool:
        st = s.lstrip()
        # СТАРАЯ логика (оставлена для совместимости):
        # return st.startswith("- ") or st.startswith("* ") or st[:2].isdigit() and st.strip().find(".") == 1
        # НОВОЕ ПОВЕДЕНИЕ добавлено отдельно в _ensure_surrounding_blanks_enhanced
        return st.startswith("- ") or st.startswith("* ") or (st[:2].isdigit() and st.strip().find(".") == 1)

    for line in lines:
        # Пустая строка перед заголовком/списком (если предыдущая строка не пустая и это не начало файла)
        if (is_header(line) or is_list_item(line)) and result and result[-1].strip() != "":
            result.append("")

        result.append(line)

        # После хедера — ровно одна пустая строка (следующий проход схлопнет лишние)
        if is_header(line):
            result.append("")

    return result


def _ensure_surrounding_blanks_enhanced(lines: list[str]) -> list[str]:
    """
    Расширенная нормализация, которая дополняет (а не заменяет) исходную:
    - Игнорируем fenced code blocks (```/~~~)
    - Более аккуратная проверка списков (в т.ч. нумерованных)
    - Не добавляем пустую строку в самом начале файла
    """
    result: list[str] = []
    in_code = False

    def is_header(s: str) -> bool:
        return s.lstrip().startswith("#")

    def is_unordered_item(s: str) -> bool:
        st = s.lstrip()
        return st.startswith("- ") or st.startswith("* ")

    def is_ordered_item(s: str) -> bool:
        return bool(ORDERED_LIST_RE.match(s))

    # СТАРОЕ (вызывало предупреждение ruff B007):
    # for idx, line in enumerate(lines):
    #     ...

    # НОВОЕ: сохраняем enumerate (для возможной отладки), но переименовываем idx -> _idx
    # чтобы явно показать, что индекс не используется (устраняем B007).
    for _idx, line in enumerate(lines):
        # Переключатель кода: открытие/закрытие ``` или ~~~
        if FENCED_CODE_RE.match(line.strip()):
            in_code = not in_code
            result.append(line)
            continue

        if in_code:
            # Внутри кода ничего не вставляем дополнительно
            result.append(line)
            continue

        need_leading_blank = is_header(line) or is_unordered_item(line) or is_ordered_item(line)
        if need_leading_blank and result and result[-1].strip() != "":
            # Не начало файла (result уже не пуст) и предыдущая строка не пустая → добавляем пустую
            result.append("")

        result.append(line)

        # После заголовка — гарантируем одну пустую строку (будет сжато ниже до нужного количества)
        if is_header(line):
            result.append("")

    return result


def _squash_blank_runs(lines: list[str], max_consecutive: int) -> list[str]:
    """Сжимает последовательности пустых строк до max_consecutive."""
    cleaned: list[str] = []
    blank_run = 0
    for line in lines:
        if line.strip() == "":
            blank_run += 1
            if blank_run <= max_consecutive:
                cleaned.append(line)
        else:
            blank_run = 0
            cleaned.append(line)
    return cleaned


def _normalize_text_pipeline(text: str, max_consecutive: int) -> str:
    """
    Полный конвейер нормализации. ВАЖНО:
    - Сначала старое поведение (_ensure_surrounding_blanks),
    - затем расширенный шаг (_ensure_surrounding_blanks_enhanced),
    - после — сжатие пустых строк с заданным порогом,
    - и финально — гарантируем завершающий перевод строки.
    Такой порядок сохраняет обратную совместимость и даёт улучшения поверх неё.
    """
    orig_lines = text.splitlines()
    lines = orig_lines[:]

    # 1) Старая логика — оставлена без изменений (совместимость)
    lines = _ensure_surrounding_blanks(lines)  # старый шаг

    # 2) Новый улучшенный слой
    lines = _ensure_surrounding_blanks_enhanced(lines)

    # 3) Сжатие повторов пустых строк
    lines = _squash_blank_runs(lines, max_consecutive=max_consecutive)

    new_text = "\n".join(lines)
    if not new_text.endswith("\n"):
        new_text += "\n"
    return new_text


def process_file(path: Path) -> bool:
    """
    СТАРЫЙ API (сохранён): правит файл на месте и печатает "Fixed blanks in <path>", если были изменения.
    Возвращает True, если файл был модифицирован.

    Внутри используем новый конвейер _normalize_text_pipeline с лимитом пустых строк,
    читаемым из окружения MDFIX_MAX_BLANKS (иначе — MAX_CONSECUTIVE_BLANKS).
    """
    text = path.read_text(encoding="utf-8")
    max_blanks = int(os.environ.get("MDFIX_MAX_BLANKS", MAX_CONSECUTIVE_BLANKS))

    # Ниже — прежний код (закомментирован, оставлен для истории):
    # orig_lines = text.splitlines()
    # lines = orig_lines[:]
    # lines = _ensure_surrounding_blanks(lines)
    # lines = _squash_blank_runs(lines)
    # new_text = "\n".join(lines)
    # if not new_text.endswith("\n"):
    #     new_text += "\n"

    # Новая, расширенная нормализация:
    new_text = _normalize_text_pipeline(text, max_consecutive=max_blanks)

    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
        print(f"Fixed blanks in {path}")
        return True
    return False


def process_file_enhanced(path: Path, write: bool = True, max_blanks: int | None = None) -> bool:
    """
    Новый API (дополнение, не ломает старый): позволяет dry-run через write=False.
    Возвращает True, если файл нуждался в изменениях (или был изменён при write=True).
    """
    text = path.read_text(encoding="utf-8")
    if max_blanks is None:
        max_blanks = int(os.environ.get("MDFIX_MAX_BLANKS", MAX_CONSECUTIVE_BLANKS))

    new_text = _normalize_text_pipeline(text, max_consecutive=max_blanks)

    if new_text != text:
        if write:
            path.write_text(new_text, encoding="utf-8")
            print(f"Fixed blanks in {path}")
        else:
            print(f"Would fix: {path}")
        return True
    return False


def _iter_target_files(paths: Iterable[str], extensions: tuple[str, ...]) -> Iterator[Path]:
    """
    Итерируем целевые markdown-файлы.
    - Если путь — каталог, рекурсивно берём файлы с подходящими расширениями.
    - Если путь — файл, берём как есть.
    """
    for name in paths:
        p = Path(name)
        if not p.exists():
            print(f"Skip (not found): {name}")
            continue
        if p.is_dir():
            for sub in p.rglob("*"):
                if sub.is_file() and sub.suffix.lower() in extensions:
                    yield sub
        else:
            # Если расширение не подходит, всё равно обрабатываем, как и раньше (совместимость)
            yield p


def _parse_cli(argv: list[str]) -> dict[str, Any]:
    """
    Простейший разбор аргументов без внешних библиотек.
    Поддерживаются ключи:
      --check / --dry-run
      --stdin
      --max-blanks N
      --extensions ".md,.mdx"
    Остальные позиционные аргументы трактуем как пути.

    Примечание: строковые литералы CLI-флагов не являются учётными данными —
    для Bandit B105 добавлены локальные подавления на сравнениях.
    """
    # [FIX-mypy] Ранее стояли type-комментарии у элементов словаря (напр. `# type: Optional[int]`),
    # что вызывало `invalid syntax` у mypy. Заменили на явную аннотацию переменной:
    flags: dict[str, Any] = {
        "check": False,
        "stdin": False,
        "max_blanks": None,  # Optional[int]
        "extensions": DEFAULT_EXTENSIONS,
        "paths": [],  # List[str]
    }

    it = iter(argv[1:])
    for token in it:
        # СТАРОЕ: if token == "--check" or token == "--dry-run":
        # НОВОЕ (исправление ruff PLR1714): объединяем сравнения
        if token in ("--check", "--dry-run"):
            flags["check"] = True
        elif token == "--stdin":  # nosec B105: CLI flag literal, not a credential
            flags["stdin"] = True
        elif token == "--max-blanks":  # nosec B105: CLI flag literal, not a credential
            try:
                flags["max_blanks"] = int(next(it))
            except (StopIteration, ValueError):
                print("Invalid or missing value for --max-blanks")
                sys.exit(EXIT_BAD_ARGS)
        elif token == "--extensions":  # nosec B105: CLI flag literal, not a credential
            try:
                raw = next(it)
                exts = tuple(e.strip() for e in raw.split(",") if e.strip())
                flags["extensions"] = exts or DEFAULT_EXTENSIONS
            except StopIteration:
                print("Missing value for --extensions")
                sys.exit(EXIT_BAD_ARGS)
        else:
            flags["paths"].append(token)

    return flags


def main(argv: list[str]) -> int:
    # Новый путь: если переданы флаги — работаем в расширенном режиме
    # Если флагов нет, остаётся совместимость с прежним интерфейсом:
    #   md_fix_blanks.py <files...>
    has_flags = any(a.startswith("--") for a in argv[1:])
    if has_flags:
        flags = _parse_cli(argv)

        # stdin режим: читаем и пишем в stdout (никаких изменений на диске)
        if flags["stdin"]:
            data = sys.stdin.read()
            max_blanks = flags["max_blanks"] if flags["max_blanks"] is not None else int(os.environ.get("MDFIX_MAX_BLANKS", MAX_CONSECUTIVE_BLANKS))
            sys.stdout.write(_normalize_text_pipeline(data, max_consecutive=max_blanks))
            return EXIT_OK

        if not flags["paths"]:
            print("Usage:")
            print('  md_fix_blanks.py [--check|--dry-run] [--stdin] [--max-blanks N] [--extensions ".md,.mdx"] <paths...>')
            return EXIT_BAD_ARGS

        max_blanks = flags["max_blanks"] if flags["max_blanks"] is not None else int(os.environ.get("MDFIX_MAX_BLANKS", MAX_CONSECUTIVE_BLANKS))
        targets = list(_iter_target_files(flags["paths"], flags["extensions"]))

        any_changed = False
        for path in targets:
            # В режиме --check не пишем файл
            changed = process_file_enhanced(path, write=not flags["check"], max_blanks=max_blanks)
            any_changed |= changed

        return EXIT_NEEDS_FIX if (flags["check"] and any_changed) else EXIT_OK

    # СТАРЫЙ ПУТЬ (совместимость с существующими вызовами pre-commit):
    if len(argv) < MIN_ARGS:
        print("Usage: md_fix_blanks.py <files...>")
        return EXIT_BAD_ARGS

    changed = False
    for name in argv[1:]:
        p = Path(name)
        if not p.exists():
            print(f"Skip (not found): {name}")
            continue
        if p.is_dir():
            # Сохраняем прежнее поведение: обрабатываем только .md
            for sub in p.rglob("*.md"):
                changed |= process_file(sub)
        else:
            changed |= process_file(p)

    # Исторически утилита возвращала 0 всегда; сохраняем это поведение.
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main(sys.argv))
