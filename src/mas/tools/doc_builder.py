# src/mas/tools/doc_builder.py
# =============================================================================
# Безопасный рефакторинг:
# - Исправлены отступы и синтаксис, добавлена базовая валидация входных данных.
# - Сохранена обратная совместимость: класс/метод/сигнатура прежние.
# - Добавлены комментарии и вспомогательный self-check (доп. функционал).
# - Ниже сохранён исходный вариант кода в комментарии для аудита.
# =============================================================================

from __future__ import annotations

from collections.abc import Iterable


class DocBuilder:
    # -------------------------------------------------------------------------
    # СТАРАЯ ВЕРСИЯ (для истории, была с неверными отступами и потому не работала):
    #
    # def build_summary(self, plan: Dict, design: Dict) -> str:
    #     return (
    #         "# Build Summary\n\n" +
    #         f"Scope: {plan.get('title')}\n\n" +
    #         "Modules:\n" + "\n".join(f"- {m}" for m in design.get('modules', [])) + "\n"
    #     )
    # -------------------------------------------------------------------------

    def build_summary(self, plan: dict, design: dict) -> str:
        """
        Формирует краткую сводку сборки.
        Backward-compatible: сигнатура не менялась, строка результата идентична по структуре,
        но входные данные безопасно нормализуются.
        """
        title = plan.get("title")  # сохраняем прежнюю семантику: может быть None — отобразится как 'None'
        modules_raw = design.get("modules", [])

        # Мягкая нормализация модулей: приводим к списку строк, но не ломаем поведение
        modules: list[str]
        if isinstance(modules_raw, str):
            # единичная строка — превращаем в один элемент
            modules = [modules_raw]
        elif isinstance(modules_raw, Iterable):
            modules = [str(m) for m in modules_raw]
        else:
            modules = [str(modules_raw)]  # на крайний случай

        # Собираем результат «как раньше» — заголовок, Scope, список модулей
        body = "# Build Summary\n\n" + f"Scope: {title}\n\n" + "Modules:\n" + "\n".join(f"- {m}" for m in modules) + "\n"
        return body

    # Дополнение (необязательное к использованию вызывающим кодом): быстрая самопроверка результата.
    def selfcheck_summary(self, summary: str) -> bool:
        """
        Простой self-check: есть ли ключевые секции, ожидаемые шаблоном.
        Не используется автоматически — безопасное дополнение.
        """
        return isinstance(summary, str) and "# Build Summary" in summary and "Scope:" in summary and "Modules:" in summary
