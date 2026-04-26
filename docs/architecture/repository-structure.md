# Структура репозитория

```text
.
├── backend/
│   ├── app/
│   └── tests/
├── frontend/
│   ├── public/
│   └── src/
├── database/
│   ├── migrations/
│   └── seeds/
├── deploy/
├── docs/
│   ├── api/
│   ├── architecture/
│   ├── devops/
│   ├── iterations/
│   ├── master-thesis/
│   ├── qa/
│   └── security/
└── tests/
```

Каталоги документации сгруппированы по назначению: архитектура, API, DevOps, QA, безопасность, отчеты по итерациям и материалы магистерской работы.

## Назначение каталогов

| Каталог | Назначение |
|---|---|
| `backend/` | FastAPI API, бизнес-логика, авторизация, работа с БД. |
| `frontend/` | React UI, маршруты, формы, списки и карточки заявок. |
| `database/` | Alembic-миграции, seed-данные и справочники. |
| `deploy/` | DevOps-конфигурация, вспомогательные deployment-артефакты. |
| `docs/` | Архитектура, требования, безопасность, материалы магистерской работы. |
| `docs/api/` | Описание REST API и ссылка на OpenAPI/Swagger. |
| `docs/devops/` | CI/CD, контейнерная поставка, DevOps-метрики. |
| `docs/iterations/` | Отчеты по выполнению итераций и критерии готовности. |
| `docs/qa/` | Тестовая стратегия и результаты проверок. |
| `backend/tests/` | Unit, API, integration, smoke и security-тесты backend. |
| `tests/` | Зарезервировано под дополнительные сквозные проверки. |
