# Frontend

React-приложение на Vite для веб-интерфейса системы заявок.

## Состав

- `src/main.jsx` - корневой React-компонент и проверка `/health`.
- `src/styles.css` - базовое оформление интерфейса.
- `package.json` - npm-скрипты и зависимости.
- `Dockerfile` - контейнер frontend-сервиса.

## Переменные окружения

Frontend использует `VITE_API_BASE_URL` для обращения к backend API.

Значение по умолчанию в Docker Compose:

```text
http://localhost:8000
```

## Локальный запуск

Рекомендуемый запуск выполняется из корня репозитория:

```bash
docker compose up --build
```

После запуска интерфейс доступен по адресу `http://localhost:5173`.
