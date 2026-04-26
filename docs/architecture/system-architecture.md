# Архитектура системы

## Назначение

Система внутренних заявок построена как учебный веб-прототип с разделением frontend, backend и базы данных. Архитектура ориентирована на повторяемый локальный запуск, проверяемые миграции, автоматические тесты и демонстрацию DevOps-процесса поставки.

## Компонентная схема

```mermaid
flowchart LR
    user[Пользователь] --> browser[Web UI React]
    browser --> api[FastAPI backend]
    api --> db[(PostgreSQL)]
    api --> notification[NotificationProvider]
    notification --> mock[Mock provider]
    notification --> max[MAX adapter]
    api --> logs[JSON logs]
    ci[GitHub Actions CI] --> tests[pytest и frontend build]
    ci --> images[Docker images]
    ci --> smoke[Smoke test /health]
    images --> compose[Docker Compose]
    compose --> browser
    compose --> api
    compose --> db
```

## Основные модули

| Модуль | Ответственность |
|---|---|
| `frontend/src` | Интерфейс входа, списки заявок, карточка заявки, комментарии, история, уведомления, отчеты. |
| `backend/app/main.py` | REST API, бизнес-правила жизненного цикла заявок, отчеты, вызов уведомлений. |
| `backend/app/auth.py` | Аутентификация, JWT, проверка текущего пользователя и ролей. |
| `backend/app/notifications.py` | Заменяемый mock/MAX-провайдер уведомлений. |
| `backend/app/structured_logging.py` | Структурированные логи и маскирование чувствительных полей. |
| `database/migrations` | Версионированная схема БД, справочники, seed-пользователи и демонстрационные заявки. |
| `.github/workflows/ci.yml` | Автоматическая проверка, сборка Docker-образов и smoke-тест. |

## Поток обработки заявки

```mermaid
sequenceDiagram
    participant E as Сотрудник
    participant UI as React UI
    participant API as FastAPI
    participant DB as PostgreSQL
    participant N as NotificationProvider
    participant A as Администратор
    participant X as Исполнитель

    E->>UI: Создает заявку
    UI->>API: POST /tickets
    API->>DB: tickets + ticket_history
    API->>N: ticket_created
    A->>API: PATCH /tickets/{id}/assign
    API->>DB: assignee_id, status assigned, history
    API->>N: ticket_assigned
    X->>API: PATCH /tickets/{id}/status in_progress
    API->>DB: status, history
    X->>API: PATCH /tickets/{id}/status completed
    API->>DB: completed_at, history
    E->>API: PATCH /tickets/{id}/status closed
    API->>DB: closed_at, history
```

## Архитектурные ограничения

- Backend является единственной точкой доступа к PostgreSQL для пользовательских сценариев.
- Все закрытые endpoint требуют JWT.
- Ролевые проверки выполняются на backend, а frontend только скрывает недоступные действия для удобства.
- В заявках, комментариях, логах, seed-данных и дампах запрещены медицинские данные пациентов.
- MAX-интеграция вынесена за интерфейс `NotificationProvider`, поэтому учебный mock-режим не требует реальных токенов.
