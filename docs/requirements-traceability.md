# Трассируемость требований

## Матрица требований, реализации и проверок

| Требование | Реализация | Проверка | Критерий приемки |
|---|---|---|---|
| Вход пользователя и JWT | `POST /auth/login`, `GET /auth/me`, `backend/app/auth.py` | `test_protected_endpoint_requires_authentication`, unit-тесты ролей | Закрытые API недоступны без токена. |
| Ролевой доступ | `require_roles`, проверки в endpoint заявок и отчетов | `test_employee_cannot_assign_ticket`, `test_manager_role_cannot_use_ticket_list` | Пользователь выполняет только действия своей роли. |
| Создание заявки сотрудником | `POST /tickets` | `test_employee_can_create_ticket` | Заявка создается со статусом `created` и рассчитанным SLA. |
| Просмотр заявок с учетом роли | `GET /tickets`, `GET /tickets/{id}` | `test_unassigned_executor_cannot_read_someone_elses_ticket` | Чужая заявка недоступна без роли администратора или участия в заявке. |
| Назначение исполнителя | `PATCH /tickets/{id}/assign` | `test_admin_assigns_executor` | Администратор назначает активного пользователя с ролью `executor`. |
| Жизненный цикл статусов | `PATCH /tickets/{id}/status`, `ALLOWED_STATUS_TRANSITIONS` | `test_ticket_status_lifecycle`, `test_invalid_status_transition_is_rejected` | Разрешены только переходы `created -> assigned -> in_progress -> completed -> closed`. |
| История заявки | `ticket_history`, `GET /tickets/{id}/history` | `test_ticket_comments_history_and_notifications` | Ключевые события видны в истории. |
| Комментарии | `ticket_comments`, endpoints comments | `test_ticket_comments_history_and_notifications` | Комментарий сохраняется и возвращается API. |
| Mock/MAX-уведомления | `NotificationProvider`, `notification_logs` | `test_mock_notification_provider_returns_sent_result`, API-тест уведомлений | События уведомлений сохраняют статус отправки. |
| SLA и просрочки | `sla_due_at`, `is_overdue`, `/reports/summary` | `test_manager_report_includes_sla_overdue_ticket` | Отчет показывает просроченные открытые заявки. |
| Отчеты руководителя | `GET /reports/summary`, frontend reports panel | API-тест отчета, frontend build | Руководитель и администратор получают статистику. |
| Контейнерный запуск | `docker-compose.yml`, Dockerfile backend/frontend | CI `docker compose build`, smoke `/health` | Сервисы запускаются одной командой. |
| CI/CD | `.github/workflows/ci.yml` | GitHub Actions или локальные команды | Тесты, миграции, сборки и smoke-тест выполняются в pipeline. |
| Запрет секретов и медицинских данных | `docs/security`, structured logging redaction | `test_structured_log_fields_redact_secrets` | Токены, пароли и данные пациентов не попадают в репозиторий и логи. |

## Использование в магистерской работе

Эта матрица связывает требования, программные модули, тесты и критерии приемки. Ее можно использовать в разделе валидации результата, чтобы показать, что реализация проверяется не только вручную, но и автоматизированными тестами.
