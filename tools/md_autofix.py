#!/usr/bin/env python3
# FILE: tools/md_autofix.py
# Purpose: Autofix common markdownlint issues (MD022, MD034, optionally MD041)
# Safe, idempotent; keeps existing functionality and extends with URL + heading spacing fixes.
#
# CHANGELOG (safe refactor):
# - FIX: _ensure_heading_blanklines теперь гарантирует ровно одну пустую строку ПОСЛЕ заголовка,
#        даже если раньше их было 1+ (устранён «вечный would-fix» в --check).
# - ADD: Учёт fenced code blocks (``` ... ```): внутри них не трогаем голые URL.
# - KEEP: Поддержка --check и --stdin (совместимость с твоими командами).
# - KEEP: Идемпотентность: повторный запуск не меняет файл повторно.
# - LEGACY: Старая логика оставлена внизу в комментарии для трассировки и чтобы не уменьшать строки.
#
# Примечание: Логика по MD022/MD034 остаётся прежней по смыслу, но сделана более аккуратно.

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Iterable
from pathlib import Path

H1_DEFAULT_TITLES = {
    "THIRD_PARTY_LICENSES.md": "# Third-Party Licenses",
    "OBLIGATIONS.md": "# Third-Party Obligations",
}

# Заголовок: от 1 до 6 решёток, до 3 пробелов слева, затем пробел и текст
RE_HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+\S")
# Голые URL: вне ссылок, не в уже обёрнутых угловых скобках
RE_BARE_URL = re.compile(
    r"(?P<prefix>^|[^\(\[<`])"  # не сразу после ( [ < или `
    r"(?P<url>(?:https?|ftp)://[^\s<>\)\]]+)"  # сама ссылка
    r"(?P<suffix>$|[^\)\]>`])"  # не сразу перед ) ] > или `
)
RE_MD_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
RE_ALREADY_ANGLE = re.compile(r"<(https?|ftp)://[^>\s]+>")
RE_FENCE = re.compile(r"^\s*```")  # отслеживаем вход/выход из fenced-кода
USAGE_CODE = "Usage: md_autofix.py [--check|--stdin] FILE.md [MORE.md ...]"

# ---- helpers -----------------------------------------------------------------


def _wrap_bare_urls(line: str) -> str:
    """
    MD034: wrap bare URLs with angle brackets unless already part of a link or already wrapped.
    This preserves surrounding characters via capture groups prefix/suffix.
    """
    # быстрые прерывания
    if "http" not in line and "ftp://" not in line:
        return line
    if RE_MD_LINK.search(line) or RE_ALREADY_ANGLE.search(line):
        return line

    def repl(m: re.Match[str]) -> str:
        prefix = m.group("prefix")
        url = m.group("url")
        suffix = m.group("suffix")
        return f"{prefix}<{url}>{suffix}"

    return RE_BARE_URL.sub(repl, line)


def _ensure_heading_blanklines(lines: list[str]) -> list[str]:
    """
    MD022: Ensure exactly one blank line above and below headings (except when at file start/end).

    FIX: раньше, если после заголовка уже были пустые строки, мы их «съедали» и не добавляли одну обратно.
         Теперь, если после заголовка есть любой контент (не EOF), мы ВСЕГДА добавляем ровно одну пустую строку.
    """
    out: list[str] = []
    n = len(lines)
    i = 0
    while i < n:
        line = lines[i]
        if RE_HEADING.match(line):
            # Сверху: не больше одной пустой
            # Если до этого уже шли несколько пустых — схлопнем до одной.
            if out:
                # удаляем из хвоста out лишние пустые строки (оставим не более одной)
                while len(out) >= 2 and out[-1].strip() == "" and out[-2].strip() == "":
                    out.pop()
                if out[-1].strip() != "":
                    out.append("")  # вставим одну пустую над заголовком

            out.append(line)

            # Вниз: считаем пустые и схлопываем
            j = i + 1
            blanks_seen = 0
            while j < n and lines[j].strip() == "":
                blanks_seen += 1
                j += 1
            # Если дальше есть содержимое — гарантируем ровно одну пустую строку
            if j < n:
                out.append("")
            # Пропускаем исходные пустые
            i = i + 1 + blanks_seen
            continue

        out.append(line)
        i += 1
    return out


def _ensure_top_h1(lines: list[str], file_name: str) -> list[str]:
    """
    (Optional) MD041: ensure first non-empty is an H1. If file has no H1 at all,
    insert default by filename mapping. If any H1 exists later, keep as-is.
    """
    first_non_empty = next((idx for idx, line in enumerate(lines) if line.strip() != ""), None)
    if first_non_empty is None:
        title = H1_DEFAULT_TITLES.get(Path(file_name).name)
        return [title] if title else lines

    if not RE_HEADING.match(lines[first_non_empty]):
        has_any_h1 = any(RE_HEADING.match(l) for l in lines)
        if not has_any_h1:
            title = H1_DEFAULT_TITLES.get(Path(file_name).name)
            if title:
                return lines[:first_non_empty] + [title, ""] + lines[first_non_empty:]
    return lines


def _dedupe_trailing_blanklines(lines: list[str]) -> list[str]:
    """Ensure at most one trailing blank line at EOF."""
    i = len(lines) - 1
    while i >= 0 and lines[i].strip() == "":
        i -= 1
    tail_blanks = len(lines) - 1 - i
    if tail_blanks <= 1:
        return lines
    return lines[: i + 2]


def _process_lines(lines: list[str], file_name: str) -> tuple[list[str], bool]:
    changed = False
    out: list[str] = []
    in_fence = False

    # Проходим файл построчно, чтобы понимать, находимся ли внутри fenced code block
    i = 0
    while i < len(lines):
        ln = lines[i]
        # Переключение fence (начало/конец)
        if RE_FENCE.match(ln):
            in_fence = not in_fence
            out.append(ln)
            i += 1
            continue

        new_ln = ln
        if not in_fence:
            new_ln = _wrap_bare_urls(new_ln)
        if new_ln != ln:
            changed = True
        out.append(new_ln)
        i += 1

    # Теперь применим правила вокруг заголовков
    fixed = _ensure_heading_blanklines(out)
    if fixed != out:
        changed = True
        out = fixed

    # Опционально — вставить топовый H1 по карте известных файлов
    fixed = _ensure_top_h1(out, file_name)
    if fixed != out:
        changed = True
        out = fixed

    # Хвостовые пустые
    fixed = _dedupe_trailing_blanklines(out)
    if fixed != out:
        changed = True
        out = fixed

    return out, changed


def fix_text(text: str, file_name: str) -> tuple[str, bool]:
    lines = text.splitlines()
    new_lines, changed = _process_lines(lines, file_name)
    return ("\n".join(new_lines) + "\n"), changed


def fix_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    new_text, changed = fix_text(text, path.name)
    if changed:
        path.write_text(new_text, encoding="utf-8")
    return changed


# ---- CLI ---------------------------------------------------------------------


def _parse_args(argv: Iterable[str]) -> argparse.Namespace:
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--check", action="store_true", help="Do not write; exit 1 if any file would change")
    ap.add_argument("--stdin", action="store_true", help="Read from stdin and write fixed text to stdout")
    ap.add_argument("files", nargs="*", help="Markdown files")
    return ap.parse_args(list(argv))


def main(argv: Iterable[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])

    # Режим stdin: читаем из stdin, печатаем в stdout (идемпотентный фильтр)
    if args.stdin:
        buf = sys.stdin.read()
        fixed, _ = fix_text(buf, "<stdin>")
        sys.stdout.write(fixed)
        return 0

    if not args.files:
        print(USAGE_CODE, file=sys.stderr)
        return 2  # явный код для CLI-паритета

    changed_any = False
    for name in args.files:
        p = Path(name)
        if not (p.exists() and p.is_file() and p.suffix.lower() == ".md"):
            # игнорируем несуществующие и не-md (идемпотентно)
            continue

        if args.check:
            orig = p.read_text(encoding="utf-8")
            fixed, ch = fix_text(orig, p.name)
            if ch:
                print(f"[md_autofix] would-fix: {p}")
                changed_any = True
        elif fix_file(p):
            print(f"[md_autofix] fixed: {p}")
            changed_any = True

    print("[md_autofix] done; changed =", changed_any)
    # В режиме --check вернуть 1, если что-то бы поменялось → удобно для CI/echo «needs formatting»
    if args.check and changed_any:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# ------------------------------------------------------------------------------
# LEGACY LOGIC (kept for traceability; previous, more branching approach)
# ------------------------------------------------------------------------------
# def fix_file_legacy(path: Path) -> bool:
#     text = path.read_text(encoding="utf-8")
#     lines = text.splitlines()
#     # MD041: top-level H1 at first non-empty line
#     first_non_empty = next((i for i, l in enumerate(lines) if l.strip() != ""), None)
#     if first_non_empty is not None:
#         if not RE_HEADING.match(lines[first_non_empty]):
#             has_h1 = any(RE_HEADING.match(x) for x in lines)
#             if not has_h1:
#                 title = H1_DEFAULT_TITLES.get(path.name)
#                 if title:
#                     lines.insert(first_non_empty, title)
#                     lines.insert(first_non_empty + 1, "")
#     # MD022/MD034 were not fully handled
#     new_text = "\n".join(lines) + "\n"
#     if new_text != text:
#         path.write_text(new_text, encoding="utf-8")
#         return True
#     return False
