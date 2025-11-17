#!/usr/bin/env bash
set -euo pipefail

RED="\033[31m"; GREEN="\033[32m"; RESET="\033[0m"; BOLD="\033[1m"
fail(){ echo -e "${RED}FAIL:${RESET} $1"; exit 1; }
ok(){   echo -e "${GREEN}OK:${RESET} $1"; }

declare -a FILES=(
  "workspace/research/factsheet_devforge_mas.md"
  "workspace/brief.md"
  "workspace/acceptance_criteria.md"
  "workspace/adr/ADR-001.md"
  "workspace/adr/ADR-002.md"
  "workspace/adr/ADR-003.md"
  "workspace/wbs.md"
)

for f in "${FILES[@]}"; do
  [[ -f "$f" ]] || fail "Файл отсутствует: $f"
  [[ -s "$f" ]] || fail "Файл пустой: $f"
done
ok "Все файлы на месте и не пустые"

grep -qE '^# FactSheet' workspace/research/factsheet_devforge_mas.md || fail "factsheet: нет заголовка # FactSheet"
grep -qE '^## Assumptions' workspace/research/factsheet_devforge_mas.md || fail "factsheet: нет секции Assumptions"
grep -qE '^## References' workspace/research/factsheet_devforge_mas.md || fail "factsheet: нет секции References"
grep -qE '^## Comparable Apps' workspace/research/factsheet_devforge_mas.md || fail "factsheet: нет секции Comparable Apps"
grep -qE '^## Risks' workspace/research/factsheet_devforge_mas.md || fail "factsheet: нет секции Risks"

grep -q 'Stage: Researcher' workspace/acceptance_criteria.md || fail "AC: нет «Stage: Researcher»"
grep -qi 'выполнено' workspace/acceptance_criteria.md || fail "AC: нет статуса «выполнено»"

grep -qE '^# ADR-001' workspace/adr/ADR-001.md || fail "ADR-001: нет заголовка"
grep -qE '^# ADR-002' workspace/adr/ADR-002.md || fail "ADR-002: нет заголовка"
grep -qE '^# ADR-003' workspace/adr/ADR-003.md || fail "ADR-003: нет заголовка"

grep -qE '^# WBS' workspace/wbs.md || fail "WBS: нет заголовка # WBS"
grep -qi 'Researcher' workspace/wbs.md || fail "WBS: нет этапа Researcher"
grep -qi 'Статус' workspace/wbs.md || fail "WBS: нет строки статуса"

echo -e "${BOLD}Сводка:${RESET}"
echo " - Файлов: ${#FILES[@]} (все пройдены)"
echo " - AC/ADR/WBS/FactSheet: структура и ключевые секции на месте"
echo -e "${GREEN}Этап Researcher: ПРОЙДЕН${RESET}"
