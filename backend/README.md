# Backend

FastAPI-приложение системы внутренних заявок.

## Состав

- `app/main.py` - точка входа FastAPI.
- `app/config.py` - настройки из переменных окружения.
- `app/db.py` - асинхронное подключение к PostgreSQL.
- `alembic.ini` - конфигурация миграций Alembic.
- `Dockerfile` - контейнер backend-сервиса.

## Healthcheck

Endpoint `/health` проверяет доступность API и выполняет простой запрос к базе данных.

```bash
curl http://localhost:8000/health
```

Ожидаемый ответ:

```json
{
  "status": "ok",
  "service": "devops-ticket-system",
  "environment": "local",
  "database": "ok"
}
```

## Локальный запуск

Рекомендуемый запуск выполняется из корня репозитория:

```bash
docker compose up --build
```
