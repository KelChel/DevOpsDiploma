# Тестовая стратегия

## Цель

Тестовая стратегия подтверждает, что MVP-сценарий заявок, ролевой доступ, миграции, уведомления, SLA и отчеты работают как единый контур.

## Уровни проверок

| Уровень | Файлы | Что проверяется |
|---|---|---|
| Smoke | `test_api_ticket_lifecycle.py::test_health` | Доступность backend и подключение к БД. |
| Unit | `test_unit_rules.py` | Переходы статусов, роли, доступ к заявке, получатели уведомлений, маскирование секретов. |
| API | `test_api_ticket_lifecycle.py` | Создание заявки, назначение, смена статусов, комментарии, история, уведомления, отчеты. |
| Integration | `test_integration_database.py` | Применение миграций и наличие seed-справочников. |
| Security | `test_security_access.py` | Запрет доступа без токена, запрет чужих заявок и действий вне роли. |
| Frontend build | `npm --prefix frontend run build` | Production-сборка React-приложения. |

## Команды

```bash
docker compose up -d postgres backend
docker compose exec backend pytest
npm --prefix frontend run build
```

## Покрытые риски

| Риск | Проверка |
|---|---|
| Пользователь получает чужую заявку | `test_unassigned_executor_cannot_read_someone_elses_ticket`. |
| Действие выполняется не той ролью | `test_employee_cannot_assign_ticket`, `test_manager_role_cannot_use_ticket_list`. |
| Недопустимый переход статуса | `test_invalid_status_transition_is_rejected`, `test_status_transitions_match_lifecycle`. |
| Миграции не применяются | `test_migrations_are_applied_to_head`. |
| Уведомления раскрывают секреты | `test_unconfigured_max_provider_fails_without_secret_leak`. |
| Логи получают чувствительные поля | `test_structured_log_fields_redact_secrets`. |
| SLA и отчеты расходятся с данными | `test_manager_report_includes_sla_overdue_ticket`. |

## Критерии успешной проверки

- Все backend-тесты проходят без пропусков и ошибок.
- Frontend production-сборка завершается успешно.
- Миграции применяются на чистую БД.
- Smoke-тест `/health` возвращает статус `ok` и `database=ok`.
- Security-тесты подтверждают запрет неавторизованных и неролевых действий.
