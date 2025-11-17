# tests/conftest.py
# Назначение: аккуратно добавить <repo_root>/src в sys.path,
# чтобы импорт `from mas ...` работал при запуске pytest из корня.
# Это не требует установки пакета в editable-mode и не влияет на прод.

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
_src_str = str(_SRC)

# Вставляем в начало, чтобы перекрыть случайные конфликты путей.
if _SRC.exists() and _src_str not in sys.path:
    sys.path.insert(0, _src_str)

# --- Legacy note ---
# Если позже вы решите ставить пакет в editable-mode:
#   pip install -e .
# Тогда этот conftest можно оставить — он не мешает.
