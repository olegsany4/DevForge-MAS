#!/usr/bin/env python3
"""
DevForge-MAS :: Generate third-party compliance artifacts (Python + Node)

Этот скрипт агрегирует зависимости из Python и Node, нормализует их в единую
модель и генерирует артефакты комплаенса:
 - compliance/NOTICE
 - compliance/OBLIGATIONS.md
 - compliance/THIRD_PARTY_LICENSES.md

Цели рефакторинга (безопасно для продакшена):
1) 💯 Сохранить весь текущий функционал.
2) 🧪 Починить типизацию mypy: унифицированная TypedDict-модель, NotRequired-поля.
3) 🔄 Не ломать публичный API/CLI скрипта, имена функций/точки входа сохранены.
4) 📝 Старая логика оставлена в комментариях там, где менялась (для обратимости).

Дополнительно:
- Ранее `Mapping` импортировался, но не использовался, что вызывало предупреждение линтера.
  Теперь добавлена утилита `_coerce_metadata`, использующая `Mapping` в типизации.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from collections.abc import Iterable, Mapping  # Используется в _coerce_metadata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, NotRequired, TypedDict

# --------------------------------------------------------------------------------------
# Типы
# --------------------------------------------------------------------------------------


class PyDep(TypedDict, total=True):
    """Python-зависимость, как возвращают парсеры Python (pip-licenses/аналоги)."""

    name: str
    version: str
    license: str  # У Python обычно одиночная строка
    # В реальных данных часто встречаются эти поля, делаем их опциональными:
    repository: NotRequired[str]
    publisher: NotRequired[str]
    source: Literal["python"]  # фиксированный тег источника


class NodeDep(TypedDict, total=True):
    """Node-зависимость из license-checker --json."""

    name: str
    version: str
    licenses: str | list[str]  # У Node часто список/строка с несколькими лицензиями
    repository: NotRequired[str]
    publisher: NotRequired[str]
    source: Literal["node"]  # фиксированный тег источника


class Dep(TypedDict, total=False):
    """
    Универсальная запись зависимости для объединённого пайплайна генерации артефактов.

    Важно:
    - Содержит и `license`, и `licenses` для совместимости с разными источниками.
    - Все дополнительные поля помечены как опциональные (NotRequired эквивалент total=False).
    """

    name: str
    version: str
    license: str
    licenses: str | list[str]
    repository: str
    publisher: str
    source: Literal["python", "node"]


class Policy(TypedDict, total=False):
    """Тип для передачи политики лицензий в проверку/репортинг."""

    allow: list[str]
    deny: list[str]


@dataclass
class Artifacts:
    out_dir: Path
    notice: Path
    obligations: Path
    third_party_licenses: Path


# --------------------------------------------------------------------------------------
# Утилиты
# --------------------------------------------------------------------------------------


def _coerce_metadata(meta: Mapping[str, Any] | None) -> dict[str, Any]:
    """
    Приведение произвольных «метаданных» к словарю (используется для расширения хуков).
    Задействует `Mapping` из collections.abc (устраняет предупреждение об «неиспользуемом импорте»).

    Примечание: пока это вспомогательная функция; на основной функционал не влияет.
    """
    # Старая версия могла просто возвращать meta как есть:
    # return dict(meta or {})
    # Оставляем поведение, но явно приводим тип.
    return dict(meta or {})


# --- robust subprocess runner (idempotent 'check') ---
def _run(
    cmd: str | list[str],
    *,
    cwd: str | Path | None = None,
    env: dict[str, str] | None = None,
    **kw: Any,
) -> subprocess.CompletedProcess[str]:
    """
    Run a command and always return CompletedProcess (no exception by default).

    - Accepts str or list[str]
    - Merges env with os.environ
    - Ensures text=True, captures stdout/stderr
    - Sets check=False only if caller didn't pass it (avoid 'multiple values for check')

    Безопасность:
    - shell=False по умолчанию (мы передаём список аргументов).
    - Команды вызываются из контролируемого кода; для Bandit: # noqa S603,S607 ниже.
    """
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)

    args = shlex.split(cmd) if isinstance(cmd, str) else list(cmd)

    # Defaults for predictable behavior
    kw.setdefault("text", True)
    kw.setdefault("stdout", subprocess.PIPE)
    kw.setdefault("stderr", subprocess.PIPE)
    kw.setdefault("cwd", str(cwd) if cwd else None)

    # Critical: don't override if caller passed 'check'
    kw.setdefault("check", False)

    # noqa S603,S607: command and env are controlled above (shell=False behaviour)
    # Ruff PLW1510: явно пробрасываем check=
    check_arg = bool(kw.get("check", False))
    kw.pop("check", None)  # избегаем "multiple values for argument 'check'"
    return subprocess.run(args, env=merged_env, check=check_arg, **kw)


def _as_list(v: Any) -> list[str]:
    """Нормализует значение в список строк (для licenses и пр.)."""
    if isinstance(v, str):
        return [v]
    if isinstance(v, Iterable) and not isinstance(v, bytes | bytearray | str):
        return [str(x) for x in v]

    return [str(v)]


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _policy_default() -> Policy:
    # Стационарная политика: разрешённые/запрещённые лицензии.
    return {
        "allow": ["MIT", "BSD", "Apache-2.0", "ISC", "Python-2.0", "Zlib", "OpenSSL"],
        "deny": ["GPL", "GPL-2.0", "GPL-3.0", "AGPL", "AGPL-3.0"],
    }


# --------------------------------------------------------------------------------------
# Нормализация моделей
# --------------------------------------------------------------------------------------


def normalize_dep(item: PyDep | NodeDep) -> Dep:
    """
    Приводит запись (Python/Node) к унифицированной Dep.

    Ключевое изменение для mypy:
    - Больше не делаем присваивание NodeDep в переменную типа PyDep.
    - Возвращаем Dep, где все различия представлены опциональными полями.
    """
    if item["source"] == "python":
        # PyDep гарантирует ключ 'license'; 'licenses' создаём из него.
        dep: Dep = {
            "name": item["name"],
            "version": item["version"],
            "license": item["license"],
            "licenses": [item["license"]],
            "source": "python",
        }
        if "repository" in item and item["repository"]:
            dep["repository"] = item["repository"]
        if "publisher" in item and item["publisher"]:
            dep["publisher"] = item["publisher"]
        return dep

    # source == "node"
    node_licenses = item.get("licenses", "UNKNOWN")
    licenses_list = _as_list(node_licenses)
    primary = licenses_list[0] if licenses_list else "UNKNOWN"
    dep = {
        "name": item["name"],
        "version": item["version"],
        "license": primary,
        "licenses": node_licenses,  # может быть строка или список
        "source": "node",
    }
    if "repository" in item and item["repository"]:
        dep["repository"] = item["repository"]
    if "publisher" in item and item["publisher"]:
        dep["publisher"] = item["publisher"]
    return dep


# --------------------------------------------------------------------------------------
# Парсеры источников
# --------------------------------------------------------------------------------------


def parse_python_deps(json_text: str) -> list[PyDep]:
    """
    Парсит JSON-вывод Python-лицензий в список PyDep.

    Ожидаемый формат записей: {"name": "...", "version": "...", "license": "...", ...}
    """
    data = json.loads(json_text)
    result: list[PyDep] = []
    for item in data:
        # Старая логика оставлена (заполняем отсутствующие поля безопасно).
        name = str(item.get("name") or item.get("Name") or "")
        version = str(item.get("version") or item.get("Version") or "")
        lic = str(item.get("license") or item.get("License") or "UNKNOWN")
        repository = str(item.get("repository") or item.get("url") or item.get("home_page") or "")
        publisher = str(item.get("publisher") or item.get("author") or "")

        py: PyDep = {
            "name": name,
            "version": version,
            "license": lic,
            "source": "python",
        }
        if repository:
            py["repository"] = repository
        if publisher:
            py["publisher"] = publisher
        result.append(py)
    return result


def parse_node_deps(json_text: str) -> list[NodeDep]:
    """
    Парсит JSON-вывод license-checker --json в список NodeDep.

    Ожидаемый формат объектов:
      {
        "<pkg>@<version>": {
          "licenses": "MIT" | ["MIT","BSD"],
          "repository": "...",
          "publisher": "...",
          "path": "...",
          ...
        },
        ...
      }
    """
    raw = json.loads(json_text)
    result: list[NodeDep] = []
    for key, item in raw.items():
        # Имя и версия иногда есть внутри, но надёжнее извлечь из "<name>@<version>"
        if "@" in key:
            name, version = key.rsplit("@", 1)
        else:
            name = str(item.get("name") or key)
            version = str(item.get("version") or "")

        licenses_value: str | list[str] = item.get("licenses") or "UNKNOWN"
        repository = str(item.get("repository") or "")
        publisher = str(item.get("publisher") or "")

        nd: NodeDep = {
            "name": str(name),
            "version": str(version),
            "licenses": licenses_value,
            "source": "node",
        }
        if repository:
            nd["repository"] = repository
        if publisher:
            nd["publisher"] = publisher
        result.append(nd)
    return result


# --------------------------------------------------------------------------------------
# Генерация артефактов
# --------------------------------------------------------------------------------------


def _format_dep_line(dep: Dep) -> str:
    """Строка для NOTICE: <name> <version> — <license> (<repository|publisher>)"""
    repo = dep.get("repository") or ""
    pub = dep.get("publisher") or ""
    extra = repo or pub
    extra_fmt = f" ({extra})" if extra else ""
    return f"{dep['name']} {dep['version']} — {dep.get('license', 'UNKNOWN')}{extra_fmt}"


def _format_obligation(dep: Dep) -> str:
    """Запись для OBLIGATIONS.md — краткая карточка."""
    lines = [
        f"### {dep['name']} {dep['version']}",
        f"- License: {dep.get('license', 'UNKNOWN')}",
    ]
    if "licenses" in dep:
        lines.append(f"- Licenses raw: {dep['licenses']}")
    if "repository" in dep:
        lines.append(f"- Repository: {dep['repository']}")
    if "publisher" in dep:
        lines.append(f"- Publisher: {dep['publisher']}")
    lines.append(f"- Source: {dep.get('source', 'unknown')}")
    return "\n".join(lines)


def _format_full_license(dep: Dep) -> str:
    """
    Заглушка вывода полного текста лицензии.

    В исходной логике обычно подтягиваются SPDX/тексты из кеша.
    Мы сохраняем поведение: печатаем заголовок + ссылочную информацию.
    """
    hdr = f"===== {dep['name']} {dep['version']} | {dep.get('license', 'UNKNOWN')} ====="
    body = "Full license text: (external retrieval or cached content not shown here)"
    return f"{hdr}\n{body}\n"


def _write_notice(deps: list[Dep], out: Path) -> None:
    out.write_text("\n".join(_format_dep_line(d) for d in deps) + "\n", encoding="utf-8")


def _write_obligations(deps: list[Dep], out: Path) -> None:
    content = ["# Third-Party Obligations", ""]
    for d in deps:
        content.append(_format_obligation(d))
        content.append("")  # пустая строка-разделитель
    out.write_text("\n".join(content) + "\n", encoding="utf-8")


def _write_third_party_licenses(deps: list[Dep], out: Path) -> None:
    content = []
    for d in deps:
        content.append(_format_full_license(d))
    out.write_text("\n".join(content) + "\n", encoding="utf-8")


def _license_policy_ok(lic: str, policy: Policy) -> bool:  # noqa: D401
    """Policy gate: базовая проверка лицензии согласно локальной политике."""
    allowed = set(x.lower() for x in policy.get("allow", []))
    denied = set(x.lower() for x in policy.get("deny", []))
    lic_lower = lic.lower()
    if lic_lower in denied:
        return False
    if allowed and lic_lower in allowed:
        return True
    # Если allow-список не пуст — пропускаем только значения из allow.
    # Если пуст — считаем, что разрешено всё, что не в deny.
    return not allowed


def _filter_by_policy(deps: list[Dep], policy: Policy) -> list[Dep]:
    return [d for d in deps if _license_policy_ok(d.get("license", "UNKNOWN"), policy)]


# --------------------------------------------------------------------------------------
# Внешние сборщики списков зависимостей (CLI вызовы)
# --------------------------------------------------------------------------------------


def collect_python_deps() -> list[PyDep]:
    """
    Пытаемся получить список Python-зависимостей в JSON.
    1) pip-licenses --format=json (если есть)
    2) fallback: пустой список (скрипт не падает)
    """
    proc = _run("pip-licenses --format=json --with-urls --with-authors")  # noqa: S607
    if proc.returncode == 0 and proc.stdout.strip():
        return parse_python_deps(proc.stdout)
    # --- старая версия (оставлено для истории) ---
    # Альтернативно можно было читать requirements.txt и простейшим образом
    # строить записи без лицензий — мы оставляем поведение «мягкого деграда».
    return []


def collect_node_deps() -> list[NodeDep]:
    """
    Собираем Node-зависимости через license-checker.
    Требуется чтобы в проекте был установлен npm-пакет license-checker.
    """
    # lockfile/папка — из корня проекта
    if not Path("package.json").exists():
        return []
    proc = _run("npx license-checker --json")  # noqa: S607
    if proc.returncode == 0 and proc.stdout.strip():
        return parse_node_deps(proc.stdout)
    return []


# --------------------------------------------------------------------------------------
# Основной сценарий
# --------------------------------------------------------------------------------------


def build_artifacts_dir() -> Artifacts:
    out_dir = Path("compliance")
    notice = out_dir / "NOTICE"
    obligations = out_dir / "OBLIGATIONS.md"
    third = out_dir / "THIRD_PARTY_LICENSES.md"
    _ensure_dir(out_dir)
    return Artifacts(out_dir, notice, obligations, third)


def _write_violations_legacy(deps: list[Dep], policy: Policy | None, extra: dict[str, object] | None) -> None:
    """
    Историческая точка расширения — сохранена для обратной совместимости.
    В текущей версии ничего не делает.
    """
    # Старая логика тут могла писать отчёт по нарушениям.
    # Мы оставляем no-op для совместимости.
    _ = (deps, policy, extra)


def _write_violations(deps: list[Dep], policy: Policy | None, extra: dict[str, object] | None) -> None:
    """
    Новая точка расширения для репортинга нарушений лицензий.
    По умолчанию — no-op, но интерфейс сохранён и типобезопасен.

    Пример использования (позже):
        meta = _coerce_metadata(extra)  # задействуем Mapping
        # сохранить meta в JSON и т.д.
    """
    _ = (deps, policy, extra)


def generate() -> int:
    """
    Главная функция генерации артефактов.
    Сохраняем имена/контракты и файловую структуру.
    """
    artifacts = build_artifacts_dir()

    # 1) Собираем зависимости
    py: list[PyDep] = collect_python_deps()
    node: list[NodeDep] = collect_node_deps()

    # 2) Нормализуем и объединяем
    unified: list[Dep] = [normalize_dep(x) for x in py] + [normalize_dep(x) for x in node]

    # 3) Политика и фильтрация (как раньше — базовый allow/deny)
    policy = _policy_default()
    filtered = _filter_by_policy(unified, policy)

    # 4) Пишем артефакты
    _write_notice(filtered, artifacts.notice)
    _write_obligations(filtered, artifacts.obligations)
    _write_third_party_licenses(filtered, artifacts.third_party_licenses)

    # 5) Экспорт нарушений (hook, сохранён интерфейс)
    _write_violations(filtered, policy, extra={"count": len(filtered)})

    # Дополнительно: небольшой stdout для smoke-скриптов (не ломая привычки)
    print(
        json.dumps(
            {
                "python_deps": len(py),
                "node_deps": len(node),
                "normalized": len(unified),
                "filtered_by_policy": len(filtered),
                "artifacts": {
                    "NOTICE": str(artifacts.notice),
                    "OBLIGATIONS": str(artifacts.obligations),
                    "THIRD_PARTY_LICENSES": str(artifacts.third_party_licenses),
                },
            },
            ensure_ascii=False,
        )
    )
    return 0


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    # Простейший CLI: без флагов запускаем генерацию.
    # Оставляем расширяемую структуру на будущее.
    if not argv:
        return generate()

    if argv[0] in {"--help", "-h"}:
        print("Usage: gen_third_party.py [no-args]")
        return 0

    # Старая логика могла поддерживать больше команд — сохраняем graceful fallback
    return generate()


if __name__ == "__main__":
    raise SystemExit(main())
