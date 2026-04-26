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
│   ├── architecture/
│   ├── iterations/
│   ├── master-thesis/
│   └── security/
└── tests/
```

## Назначение каталогов

| Каталог | Назначение |
|---|---|
| `backend/` | FastAPI API, бизнес-логика, авторизация, работа с БД. |
| `frontend/` | React UI, маршруты, формы, списки и карточки заявок. |
| `database/` | Alembic-миграции, seed-данные и справочники. |
| `deploy/` | DevOps-конфигурация, вспомогательные deployment-артефакты. |
| `docs/` | Архитектура, требования, безопасность, материалы магистерской работы. |
| `docs/iterations/` | Отчеты по выполнению итераций и критерии готовности. |
| `tests/` | Сквозные, integration и smoke-тесты. |
