import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { Activity, Database, GitBranch, Server, Ticket } from "lucide-react";
import "./styles.css";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function App() {
  const [health, setHealth] = useState({ status: "loading" });

  useEffect(() => {
    let cancelled = false;

    async function loadHealth() {
      try {
        const response = await fetch(`${apiBaseUrl}/health`);
        const data = await response.json();
        if (!cancelled) {
          setHealth({ status: response.ok ? "ok" : "error", data });
        }
      } catch (error) {
        if (!cancelled) {
          setHealth({ status: "error", message: error.message });
        }
      }
    }

    loadHealth();
    const timer = window.setInterval(loadHealth, 15000);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  const healthText =
    health.status === "ok"
      ? "API и база данных доступны"
      : health.status === "loading"
        ? "Проверка соединения"
        : "Нет соединения с API";

  return (
    <main className="app-shell">
      <aside className="sidebar" aria-label="Основная навигация">
        <div className="brand">
          <Ticket aria-hidden="true" />
          <span>DevOps Ticket System</span>
        </div>
        <nav className="nav">
          <a href="#overview" className="nav-link active">
            Обзор
          </a>
          <a href="#tickets" className="nav-link">
            Заявки
          </a>
          <a href="#users" className="nav-link">
            Пользователи
          </a>
          <a href="#settings" className="nav-link">
            Настройки
          </a>
        </nav>
      </aside>

      <section className="workspace" id="overview">
        <header className="topbar">
          <div>
            <p className="eyebrow">Итерация 1</p>
            <h1>Базовая архитектура и инфраструктура</h1>
          </div>
          <div className={`health ${health.status}`}>
            <Activity aria-hidden="true" />
            <span>{healthText}</span>
          </div>
        </header>

        <section className="status-grid" aria-label="Статус сервисов">
          <article className="status-card">
            <Server aria-hidden="true" />
            <h2>Backend API</h2>
            <p>FastAPI-сервис с endpoint `/health` и конфигурацией через переменные окружения.</p>
          </article>
          <article className="status-card">
            <Database aria-hidden="true" />
            <h2>PostgreSQL</h2>
            <p>База данных запускается в Docker Compose и проверяется backend-сервисом.</p>
          </article>
          <article className="status-card">
            <GitBranch aria-hidden="true" />
            <h2>Миграции</h2>
            <p>Alembic выполняет начальную baseline-миграцию перед стартом API.</p>
          </article>
        </section>

        <section className="panel" id="tickets">
          <h2>Каркас интерфейса</h2>
          <div className="table" role="table" aria-label="Будущие разделы MVP">
            <div role="row" className="table-row table-head">
              <span role="columnheader">Раздел</span>
              <span role="columnheader">Статус</span>
              <span role="columnheader">Итерация</span>
            </div>
            <div role="row" className="table-row">
              <span role="cell">Авторизация и роли</span>
              <span role="cell">Запланировано</span>
              <span role="cell">2</span>
            </div>
            <div role="row" className="table-row">
              <span role="cell">Жизненный цикл заявок</span>
              <span role="cell">Запланировано</span>
              <span role="cell">3</span>
            </div>
            <div role="row" className="table-row">
              <span role="cell">Комментарии и история</span>
              <span role="cell">Запланировано</span>
              <span role="cell">4</span>
            </div>
          </div>
        </section>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
