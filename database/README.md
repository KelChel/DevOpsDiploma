# Database

Каталог для миграций, seed-данных и вспомогательной документации по модели данных.

## Миграции

Alembic настроен через `backend/alembic.ini`, а сами миграции находятся в `database/migrations`.

Начальная миграция `202604260001_initial_baseline.py` фиксирует baseline схемы. Бизнес-таблицы пользователей, ролей и заявок будут добавлены в следующих итерациях согласно плану.

В Docker Compose миграции применяются автоматически перед запуском backend:

```bash
alembic upgrade head
```

## PostgreSQL

PostgreSQL запускается как сервис `postgres` в корневом `docker-compose.yml`. Backend проверяет соединение с базой через endpoint `/health`.
