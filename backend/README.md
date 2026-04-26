# Backend

FastAPI-приложение системы внутренних заявок.

## Состав

- `app/main.py` - точка входа FastAPI.
- `app/config.py` - настройки из переменных окружения.
- `app/db.py` - асинхронное подключение к PostgreSQL.
- `app/auth.py` - аутентификация, загрузка текущего пользователя и RBAC-зависимости.
- `app/security.py` - bcrypt-проверка паролей и JWT.
- `app/schemas.py` - Pydantic-схемы API.
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

## Авторизация

Итерация 2 добавляет JWT-аутентификацию и базовую проверку ролей.

| Endpoint | Назначение | Доступ |
|---|---|---|
| `POST /auth/login` | Вход по логину и паролю, выдача JWT access token. | Публичный |
| `GET /auth/me` | Профиль текущего пользователя. | Авторизованный пользователь |
| `GET /roles` | Список ролей системы. | Авторизованный пользователь |
| `GET /admin/users` | Список seed-пользователей. | Только `admin` |

Пример входа:

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"employee","password":"password"}'
```

Пример запроса закрытого endpoint:

```bash
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer <token>"
```

Демо-пользователи описаны в корневом `README.md` и `database/seeds/README.md`.

## Заявки

Итерация 3 добавляет жизненный цикл заявки.

| Endpoint | Назначение | Доступ |
|---|---|---|
| `GET /ticket-categories` | Справочник активных категорий. | Авторизованный пользователь |
| `GET /ticket-statuses` | Справочник статусов. | Авторизованный пользователь |
| `POST /tickets` | Создание заявки. | `employee` |
| `GET /tickets` | Список заявок с фильтрами по статусу, категории, исполнителю и периоду. | `employee`, `executor`, `admin` |
| `GET /tickets/{ticket_id}` | Карточка заявки. | Заявитель, назначенный исполнитель, `admin` |
| `PATCH /tickets/{ticket_id}/assign` | Назначение исполнителя. | `admin` |
| `PATCH /tickets/{ticket_id}/status` | Смена статуса по жизненному циклу. | Назначенный `executor`, заявитель при закрытии |

Допустимый путь статусов: `created` -> `assigned` -> `in_progress` -> `completed` -> `closed`.

## Локальный запуск

Рекомендуемый запуск выполняется из корня репозитория:

```bash
docker compose up --build
```
