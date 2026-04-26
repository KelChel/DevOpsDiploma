# Итерация 6. CI/CD и контейнерная поставка

## Цель

Настроить автоматизированную проверку, сборку контейнеров и smoke-тест после запуска приложения.

## Реализовано

- Создан GitHub Actions workflow `.github/workflows/ci.yml`.
- В pipeline добавлены установка зависимостей backend и frontend.
- Добавлена базовая проверка качества backend через `python -m compileall`.
- Добавлена проверка миграций Alembic командой `alembic upgrade head`.
- Добавлен запуск backend-тестов `pytest`.
- Добавлена production-сборка frontend командой `npm run build`.
- Добавлена сборка Docker-образов через `docker compose build`.
- Добавлен запуск `docker compose up -d postgres backend frontend` в CI.
- Добавлен smoke-тест `GET /health` после контейнерного запуска.
- Реализованы структурированные JSON-логи backend для ключевых событий.
- Добавлена редактирующая защита полей логов от токенов, секретов и чувствительных данных.

## Структурированные события backend

| Событие | Когда пишется | Безопасные поля |
|---|---|---|
| `ticket_created` | После создания заявки | `ticket_id`, `actor_id`, `category_id`, `priority` |
| `ticket_assigned` | После назначения исполнителя | `ticket_id`, `actor_id`, `assignee_id` |
| `ticket_status_changed` | После изменения статуса | `ticket_id`, `actor_id`, `old_status`, `new_status` |
| `notification_delivery_failed` | При ошибке провайдера уведомлений | `ticket_id`, `provider`, `recipient_user_id`, `error_message` |
| `authorization_failed` | При ошибке входа или проверки токена | `reason`, опционально `username` |

Логи не содержат название, описание или комментарии заявки, потому что эти поля могут случайно включать запрещенные медицинские данные.

## Модель CI/CD

1. Разработчик отправляет изменения в репозиторий или открывает pull request.
2. GitHub Actions поднимает PostgreSQL как service container.
3. Backend проходит установку зависимостей, compile-check, миграции и pytest.
4. Frontend проходит `npm ci` и `npm run build`.
5. Docker Compose собирает образы backend и frontend.
6. Контейнеры запускаются в тестовом режиме на нестандартных портах.
7. Smoke-тест проверяет `http://localhost:18000/health`.
8. При ошибке любого шага pipeline завершается неуспешно и блокирует поставку.

## Секреты

Реальные секреты не записываются в workflow. Для CI используется `secrets.JWT_SECRET_KEY`, а при отсутствии секрета - учебное fallback-значение только для проверки pipeline. MAX-токен в CI не требуется, потому что используется `NOTIFICATION_PROVIDER=mock`.

## Откат

В учебном режиме откат описывается как повторный запуск предыдущего успешного workflow commit или возврат к предыдущему тегу/commit с последующей пересборкой Docker-образов. Для промышленного режима этот шаг заменяется публикацией версионированных образов в registry и переключением deployment на предыдущий тег.

## Критерии готовности

- Pipeline автоматически запускается на push, pull request и вручную.
- Ошибка тестов, миграций, сборки или smoke-теста останавливает pipeline.
- Docker-образы собираются в CI.
- Smoke-тест подтверждает доступность `/health`.
- Workflow не содержит реальных секретов.
- Backend пишет структурированные JSON-логи ключевых событий.
