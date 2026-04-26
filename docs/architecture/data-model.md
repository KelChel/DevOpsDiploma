# Модель данных и ER-диаграмма

## ER-диаграмма

```mermaid
erDiagram
    roles ||--o{ user_roles : grants
    users ||--o{ user_roles : has
    users ||--o{ tickets : creates
    users ||--o{ tickets : assigned
    users ||--o{ ticket_comments : writes
    users ||--o{ ticket_history : acts
    users ||--o{ notification_logs : receives
    ticket_categories ||--o{ tickets : classifies
    ticket_statuses ||--o{ tickets : describes
    tickets ||--o{ ticket_history : records
    tickets ||--o{ ticket_comments : contains
    tickets ||--o{ notification_logs : emits

    users {
        int id PK
        string username
        string password_hash
        string full_name
        string position
        bool is_active
        timestamptz created_at
    }

    roles {
        int id PK
        string code
        string name
        string description
    }

    user_roles {
        int user_id FK
        int role_id FK
    }

    ticket_categories {
        int id PK
        string code
        string name
        string description
        bool is_active
    }

    ticket_statuses {
        int id PK
        string code
        string name
        int sort_order
    }

    tickets {
        int id PK
        string title
        text description
        string priority
        int category_id FK
        int status_id FK
        int created_by_id FK
        int assignee_id FK
        timestamptz created_at
        timestamptz updated_at
        timestamptz assigned_at
        timestamptz completed_at
        timestamptz closed_at
        timestamptz sla_due_at
    }

    ticket_history {
        int id PK
        int ticket_id FK
        string event_type
        string field_name
        text old_value
        text new_value
        int actor_id FK
        timestamptz created_at
    }

    ticket_comments {
        int id PK
        int ticket_id FK
        int author_id FK
        text body
        timestamptz created_at
    }

    notification_logs {
        int id PK
        int ticket_id FK
        string event_type
        string provider
        int recipient_user_id FK
        string status
        text error_message
        timestamptz created_at
        timestamptz sent_at
    }
```

## Справочники

| Таблица | Назначение |
|---|---|
| `roles` | Роли `employee`, `executor`, `admin`, `manager`. |
| `ticket_categories` | Категории заявок: IT, доступы, хозяйственные и организационные обращения. |
| `ticket_statuses` | Статусы `created`, `assigned`, `in_progress`, `completed`, `closed`. |

## Основные сущности

| Сущность | Назначение |
|---|---|
| `users` | Учетные записи демонстрационных пользователей. Пароли хранятся как bcrypt-хеши. |
| `tickets` | Заявки, их текущий статус, исполнитель, сроки SLA и временные отметки жизненного цикла. |
| `ticket_history` | Аудит ключевых событий: создание, назначение, смена статуса, комментарии. |
| `ticket_comments` | Текстовые комментарии участников обработки заявки. |
| `notification_logs` | Результаты отправки mock/MAX-уведомлений. |

## SLA

Срок SLA рассчитывается при создании заявки по приоритету:

| Приоритет | Срок |
|---|---:|
| `critical` | 4 часа |
| `high` | 24 часа |
| `normal` | 48 часов |
| `low` | 72 часа |

Признак просрочки не хранится отдельно. API вычисляет `is_overdue`, если `sla_due_at` меньше текущего времени, а статус не равен `completed` или `closed`.
