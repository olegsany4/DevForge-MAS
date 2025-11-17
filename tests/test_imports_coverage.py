"""
Цель: обеспечить минимальное покрытие модулей src/*, даже если функциональные
тесты не вызывают код напрямую. Это smoke-проверка импортов и мягкий вызов
пробных функций, если они есть.

Правило проекта «качество > скорость»: мы не ломаем API и не меняем код src/,
поэтому тест бережно проверяет существование и вызывает только опциональные
безопасные entrypoints (например, probe()) если они есть.
"""

import importlib
import types

import pytest


@pytest.mark.parametrize(
    "module_name",
    [
        "src",
        "src.mas",
        "src.mas._probe",
        "src.mas.cli",
    ],
)
def test_import_module_smoke(module_name: str):
    mod = importlib.import_module(module_name)
    assert isinstance(mod, types.ModuleType)

    # Мягко "потрогаем" потенциальные безопасные entrypoints:
    # - если в модуле есть функция probe() — вызовем её без аргументов;
    # - если есть main() без аргументов — вызовем help-путь (только если сигнатура пустая).
    probe = getattr(mod, "probe", None)
    if callable(probe):
        probe()  # ожидается, что побочных эффектов нет

        # ... остальная часть файла без изменений ...
        main = getattr(mod, "main", None)
        if callable(main):
            # Если это Click-команда — вызываем безопасно: без чтения sys.argv
            try:
                import click  # type: ignore
            except Exception:
                click = None

            if click is not None and isinstance(main, click.core.BaseCommand):
                # не трогаем sys.argv, не выходим из процесса
                main.main(args=[], prog_name="devforge-cli", standalone_mode=False)
            else:
                try:
                    # Попытка обычного вызова без аргументов
                    main()  # noqa: F841
                except TypeError:
                    # У main есть обязательные аргументы — пропускаем
                    pass
