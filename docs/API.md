# DevForge-MAS — краткая API-справка

> Контракты проверены: **5 endpoints**, **7 schemas** (см. `workspace/contracts/CONTRACTS.json` и `make verify-architect`).

## Базовые соглашения

- Base URL (dev): `http://localhost:8000` *(пример; уточни по `backend-dev`)*

- Content-Type: `application/json`

- Все ответы имеют поле `ok: bool` и `ts: iso8601` (если так определено в CONTRACTS.json)

## Эндпоинты (обзор)

| Метод | Путь                         | Назначение                                   | Тело запроса (схема)        | Ответ (схема)         |

|------:|------------------------------|----------------------------------------------|-----------------------------|-----------------------|

| GET   | `/health`                    | Здоровье сервиса                             | —                           | `HealthResponse`      |

| GET   | `/contracts`                 | Выгрузка активных контрактов/схем            | —                           | `ContractsResponse`   |

| POST  | `/agents/{name}/task`        | Запуск задания для агента                    | `AgentTaskRequest`          | `AgentTaskResponse`   |

| POST  | `/workflows/{id}/run`        | Старт/рестарт workflow                       | `WorkflowRunRequest`        | `WorkflowRunResponse` |

| GET   | `/artifacts/{artifact_id}`   | Получение артефакта по ID                    | —                           | `ArtifactResponse`    |

> Точные поля смотри в `CONTRACTS.json` (7 схем). Ниже — типовой шаблон.

### Примеры схем (типовой шаблон)

```json
// AgentTaskRequest (пример)
{
  "task": "build_readme",
  "params": {
    "repo_path": "workspace/",
    "strict": true
  }
}
