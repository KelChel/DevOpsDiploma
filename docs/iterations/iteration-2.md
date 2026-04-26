# Итерация 2. Пользователи, роли и авторизация

## Статус

Выполнена в базовом MVP-контуре.

## Реализованные решения

| Зона | Результат |
|---|---|
| Backend | Добавлены API `/auth/login`, `/auth/me`, `/roles`, защищенный `/admin/users`. |
| Frontend | Добавлен экран входа, хранение JWT в `localStorage`, загрузка профиля и отображение разделов по ролям. |
| База данных | Созданы таблицы `users`, `roles`, `user_roles`. |
| Безопасность | Пароли хранятся как bcrypt-хеши, JWT имеет срок жизни, закрытые API требуют Bearer token. |
| Документация | Добавлена матрица ролей и прав. |

## Seed-пользователи

| Логин | Пароль | Роль |
|---|---|---|
| `employee` | `password` | Сотрудник |
| `executor` | `password` | Исполнитель |
| `admin` | `password` | Администратор |
| `manager` | `password` | Руководитель |

## Критерии готовности

| Критерий | Статус | Артефакт |
|---|---|---|
| Пользователь может войти в систему | Выполнено | `POST /auth/login`, экран входа |
| Неавторизованный пользователь не получает доступ к закрытым API | Выполнено | `GET /auth/me`, `GET /admin/users` |
| Пользователь видит интерфейс согласно своей роли | Выполнено | `frontend/src/main.jsx` |
| Пароли не хранятся в открытом виде | Выполнено | bcrypt-хеши в seed-миграции |
| JWT имеет ограниченное время жизни | Выполнено | `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` |
| Тестовые пользователи создаются через seed-данные | Выполнено | `202604260002_users_roles_auth.py` |

## Локальная проверка

Получение токена:

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"employee","password":"password"}'
```

Проверка профиля:

```bash
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer <token>"
```

Проверка RBAC:

```bash
curl http://localhost:8000/admin/users \
  -H "Authorization: Bearer <employee-token>"
```

Ожидаемый результат для сотрудника: `403 Forbidden`.

## Следующая итерация

Итерация 3: жизненный цикл заявок.
