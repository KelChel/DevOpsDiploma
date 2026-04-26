# Database

Каталог для миграций, seed-данных и вспомогательной документации по модели данных.

## Миграции

Alembic настроен через `backend/alembic.ini`, а сами миграции находятся в `database/migrations`.

Начальная миграция `202604260001_initial_baseline.py` фиксирует baseline схемы без таблиц.

Миграция `202604260002_users_roles_auth.py` добавляет таблицы `users`, `roles`, `user_roles` и демонстрационных пользователей для ролей сотрудника, исполнителя, администратора и руководителя.

Миграция `202604260003_ticket_lifecycle.py` добавляет таблицы `tickets`, `ticket_categories`, `ticket_statuses` и начальные справочники категорий и статусов.

В Docker Compose миграции применяются автоматически перед запуском backend:

```bash
alembic upgrade head
```

## PostgreSQL

PostgreSQL запускается как сервис `postgres` в корневом `docker-compose.yml`. Backend проверяет соединение с базой через endpoint `/health`.

## Seed-данные

Описание демонстрационных пользователей находится в `database/seeds/README.md`. Пароли seed-пользователей хранятся в базе только в виде bcrypt-хешей.
