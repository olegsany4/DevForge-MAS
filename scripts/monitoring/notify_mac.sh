#!/usr/bin/env bash
# macOS нотификация; безопасно игнорирует ошибки
title="${1:-DevForge-MAS}"
text="${2:-Event}"
osascript -e "display notification \"$text\" with title \"$title\"" >/dev/null 2>&1 || true
