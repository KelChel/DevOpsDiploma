# Демонстрационный сценарий

## Подготовка

1. Запустить проект:

```bash
docker compose up --build
```

2. Проверить доступность:

- frontend: `http://localhost:5173`;
- backend: `http://localhost:8000/health`;
- Swagger/OpenAPI: `http://localhost:8000/docs`.

3. Использовать тестовых пользователей с паролем `password`:

| Логин | Роль |
|---|---|
| `employee` | Сотрудник |
| `admin` | Администратор |
| `executor` | Исполнитель |
| `manager` | Руководитель |

## Обязательный MVP-сценарий

1. Войти как `employee`.
2. Создать заявку без медицинских данных пациентов.
3. Убедиться, что заявка создана со статусом `created`.
4. Войти как `admin`.
5. Открыть список заявок и назначить исполнителя `executor`.
6. Убедиться, что статус изменился на `assigned`.
7. Войти как `executor`.
8. Перевести заявку в статус `in_progress`.
9. Перевести заявку в статус `completed`.
10. Добавить комментарий к заявке.
11. Войти как `employee`.
12. Закрыть выполненную заявку статусом `closed`.
13. Открыть карточку заявки и показать историю, комментарии и журнал уведомлений.

## Демонстрационный плюс

1. Войти как `manager` или `admin`.
2. Открыть панель отчетов.
3. Показать количество заявок, открытые и закрытые заявки.
4. Показать распределение по статусам и категориям.
5. Показать нагрузку исполнителей.
6. Показать SLA и список просроченных заявок.
7. Открыть Swagger/OpenAPI по адресу `http://localhost:8000/docs`.
8. Показать CI/CD workflow `.github/workflows/ci.yml`.

## Проверки перед защитой

```bash
docker compose exec backend pytest
npm --prefix frontend run build
docker compose build
curl -s http://localhost:8000/health
```

Для чистой демонстрационной базы:

```bash
docker compose down --volumes --remove-orphans
docker compose up --build
```

## Финальная приемка

Финальная локальная приемка итерации 9 выполнена 2026-04-26:

- backend-тесты: `22 passed`;
- frontend-сборка: успешно;
- Docker build: backend и frontend образы собраны;
- smoke `/health`: `status=ok`, `database=ok`;
- критичные замечания: не выявлены.
