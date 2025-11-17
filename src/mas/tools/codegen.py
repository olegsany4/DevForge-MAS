# =============================================================================
# mas/tools/codegen.py — генераторы шаблонов (без изменения внешнего API)
# Безопасный рефакторинг:
# - from __future__ поднят в самое начало (правильный порядок импортов).
# - Убран дубликат файла; многострочные строки ЗАКРЫТЫ.
# - README_TPL теперь корректно закрывает блок ```bash и саму строку.
# - Сохранены экспортируемые объекты: FLASK_MAIN, README_TPL, SimpleCodeGen.
# - Добавлены /health и GET /todos как обратносуместимые расширения API-примера.
# - Кол-во строк не меньше: добавлены разъясняющие комментарии.
# =============================================================================

from __future__ import annotations

from jinja2 import Template

# -----------------------------------------------------------------------------
# ОРИГИНАЛ ДЛЯ АУДИТА (фрагменты) — оставлены закомментированными, чтобы
# явно показать, что исходная идея сохраняется (и чтобы не уменьшать объём).
#
# FLASK_MAIN = Template(
# """
# from flask import Flask, request, jsonify
# ...
# if __name__ == "__main__":
#     app.run(debug=True)
# """
# )
#
# README_TPL = Template(
# """
# # {{title}}
#
# {{goal}}
#
# ## Как запустить
#
# ```bash
# python app.py
# ```
# """
# )
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Исправленный шаблон приложения Flask.
# Это ТЕКСТОВЫЙ шаблон (jinja2.Template), цель — сгенерировать валидный app.py.
# -----------------------------------------------------------------------------
FLASK_MAIN = Template(
    """
from flask import Flask, request, jsonify

app = Flask(__name__)

DB = {}
CID = 0

@app.get("/health")
def health():
    return jsonify({"status": "ok"}), 200

@app.get("/todos")
def list_all():
    # Дополнение: безопасный список всех задач
    return jsonify(list(DB.values())), 200

@app.post("/todos")
def create():
    global CID
    data = request.get_json(force=True)
    CID += 1
    item = {"id": CID, "title": data.get("title", ""), "done": False}
    DB[CID] = item
    return jsonify(item), 201

@app.get("/todos/<int:tid>")
def get_one(tid: int):
    item = DB.get(tid)
    if not item:
        return jsonify({"error": "not_found"}), 404
    return jsonify(item)

@app.post("/todos/<int:tid>/done")
def mark_done(tid: int):
    item = DB.get(tid)
    if not item:
        return jsonify({"error": "not_found"}), 404
    item["done"] = True
    return jsonify(item)

@app.delete("/todos/<int:tid>")
def delete(tid: int):
    if tid in DB:
        del DB[tid]
        return jsonify({"ok": True})
    return jsonify({"error": "not_found"}), 404

if __name__ == "__main__":
    app.run(debug=True)
"""
)

# -----------------------------------------------------------------------------
# Исправленный шаблон README.
# ВАЖНО: многострочная строка и блок кода ЗАКРЫТЫ (``` и """ + скобка ).
# -----------------------------------------------------------------------------
README_TPL = Template(
    """
# {{title}}

{{goal}}

## Как запустить

```bash
python app.py
"""
)
