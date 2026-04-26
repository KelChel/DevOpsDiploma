# Итерация 1. Базовая архитектура и инфраструктура

## Статус

Выполнена.

## Реализованные решения

| Зона | Результат |
|---|---|
| Backend | Создано FastAPI-приложение с endpoint `/health`. |
| Frontend | Создан React/Vite-каркас с базовой навигацией и проверкой API. |
| База данных | PostgreSQL добавлен в Docker Compose, Alembic настроен на каталог `database/migrations`. |
| DevOps | Добавлены Dockerfile для backend и frontend, создан `docker-compose.yml`. |
| Документация | Обновлены инструкции локального запуска в `README.md`, `backend/README.md`, `frontend/README.md`, `database/README.md`. |

## Критерии готовности

| Критерий | Статус | Артефакт |
|---|---|---|
| `docker compose up` запускает backend, frontend и БД | Выполнено | `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile` |
| Backend отвечает на `/health` | Выполнено | `backend/app/main.py` |
| Frontend открывается в браузере | Выполнено | `frontend/src/main.jsx`, `frontend/src/styles.css` |
| Backend может подключиться к базе данных | Выполнено | `/health` выполняет `SELECT 1` |
| Конфигурация берется из переменных окружения | Выполнено | `.env.example`, `backend/app/config.py`, `docker-compose.yml` |
| Создана начальная миграция | Выполнено | `database/migrations/versions/202604260001_initial_baseline.py` |

## Локальная проверка

Основная команда запуска:

```bash
docker compose up --build
```

Проверка API:

```bash
curl http://localhost:8000/health
```

Ожидаемый ответ содержит:

```json
{
  "status": "ok",
  "database": "ok"
}
```

## Следующая итерация

Итерация 2: пользователи, роли и авторизация.

Ожидаемые результаты следующего цикла:

- таблицы пользователей и ролей;
- seed-пользователи для демонстрации;
- API входа по логину и паролю;
- JWT и middleware авторизации;
- базовый экран входа;
- разграничение интерфейса по ролям.
