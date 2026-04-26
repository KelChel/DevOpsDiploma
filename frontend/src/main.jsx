import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  Database,
  KeyRound,
  LogOut,
  Server,
  ShieldCheck,
  Ticket,
  UserCog,
  Users,
} from "lucide-react";
import "./styles.css";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const tokenStorageKey = "devops-ticket-system-token";

const roleLabels = {
  employee: "Сотрудник",
  executor: "Исполнитель",
  admin: "Администратор",
  manager: "Руководитель",
};

const demoUsers = [
  { username: "employee", role: "Сотрудник" },
  { username: "executor", role: "Исполнитель" },
  { username: "admin", role: "Администратор" },
  { username: "manager", role: "Руководитель" },
];

function App() {
  const [health, setHealth] = useState({ status: "loading" });
  const [token, setToken] = useState(() => window.localStorage.getItem(tokenStorageKey));
  const [user, setUser] = useState(null);
  const [authError, setAuthError] = useState("");
  const [isLoggingIn, setIsLoggingIn] = useState(false);

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

  useEffect(() => {
    let cancelled = false;

    async function loadProfile() {
      if (!token) {
        setUser(null);
        return;
      }

      try {
        const response = await fetch(`${apiBaseUrl}/auth/me`, {
          headers: { Authorization: `Bearer ${token}` },
        });

        if (!response.ok) {
          throw new Error("Сессия истекла или токен недействителен");
        }

        const data = await response.json();
        if (!cancelled) {
          setUser(data);
          setAuthError("");
        }
      } catch (error) {
        if (!cancelled) {
          window.localStorage.removeItem(tokenStorageKey);
          setToken(null);
          setUser(null);
          setAuthError(error.message);
        }
      }
    }

    loadProfile();

    return () => {
      cancelled = true;
    };
  }, [token]);

  const healthText =
    health.status === "ok"
      ? "API и база данных доступны"
      : health.status === "loading"
        ? "Проверка соединения"
        : "Нет соединения с API";

  const userRoles = useMemo(() => new Set(user?.roles || []), [user]);

  async function handleLogin(event) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    setIsLoggingIn(true);
    setAuthError("");

    try {
      const response = await fetch(`${apiBaseUrl}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: formData.get("username"),
          password: formData.get("password"),
        }),
      });

      if (!response.ok) {
        throw new Error("Проверьте логин и пароль");
      }

      const data = await response.json();
      window.localStorage.setItem(tokenStorageKey, data.access_token);
      setToken(data.access_token);
      event.currentTarget.reset();
    } catch (error) {
      setAuthError(error.message);
    } finally {
      setIsLoggingIn(false);
    }
  }

  function handleLogout() {
    window.localStorage.removeItem(tokenStorageKey);
    setToken(null);
    setUser(null);
    setAuthError("");
  }

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
          <a href="#auth" className="nav-link">
            Авторизация
          </a>
          {userRoles.has("admin") && (
            <a href="#admin" className="nav-link">
              Пользователи
            </a>
          )}
          {(userRoles.has("employee") || userRoles.has("executor") || userRoles.has("admin")) && (
            <a href="#tickets" className="nav-link">
              Заявки
            </a>
          )}
        </nav>
      </aside>

      <section className="workspace" id="overview">
        <header className="topbar">
          <div>
            <p className="eyebrow">Итерация 2</p>
            <h1>Пользователи, роли и авторизация</h1>
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
            <p>Доступны `/auth/login`, `/auth/me`, `/roles` и защищенный административный API.</p>
          </article>
          <article className="status-card">
            <Database aria-hidden="true" />
            <h2>PostgreSQL</h2>
            <p>Добавлены таблицы `users`, `roles`, `user_roles` и seed-пользователи.</p>
          </article>
          <article className="status-card">
            <ShieldCheck aria-hidden="true" />
            <h2>RBAC</h2>
            <p>JWT содержит срок жизни, а закрытые API проверяют авторизацию и роль.</p>
          </article>
        </section>

        <section className="auth-layout" id="auth">
          <article className="panel">
            <div className="panel-title">
              <KeyRound aria-hidden="true" />
              <h2>Вход</h2>
            </div>

            {user ? (
              <div className="profile">
                <p className="profile-name">{user.full_name}</p>
                <p className="profile-meta">{user.position}</p>
                <div className="role-list">
                  {user.roles.map((role) => (
                    <span className="role-badge" key={role}>
                      {roleLabels[role] || role}
                    </span>
                  ))}
                </div>
                <button className="button secondary" type="button" onClick={handleLogout}>
                  <LogOut aria-hidden="true" />
                  <span>Выйти</span>
                </button>
              </div>
            ) : (
              <form className="login-form" onSubmit={handleLogin}>
                <label>
                  <span>Логин</span>
                  <input name="username" autoComplete="username" defaultValue="employee" required />
                </label>
                <label>
                  <span>Пароль</span>
                  <input name="password" type="password" autoComplete="current-password" defaultValue="password" required />
                </label>
                {authError && <p className="form-error">{authError}</p>}
                <button className="button" type="submit" disabled={isLoggingIn}>
                  <KeyRound aria-hidden="true" />
                  <span>{isLoggingIn ? "Вход" : "Войти"}</span>
                </button>
              </form>
            )}
          </article>

          <article className="panel">
            <div className="panel-title">
              <Users aria-hidden="true" />
              <h2>Демо-пользователи</h2>
            </div>
            <div className="compact-table" role="table" aria-label="Демо-пользователи">
              {demoUsers.map((item) => (
                <div className="compact-row" role="row" key={item.username}>
                  <span role="cell">{item.username}</span>
                  <span role="cell">{item.role}</span>
                </div>
              ))}
            </div>
          </article>
        </section>

        <section className="panel" id="tickets">
          <div className="panel-title">
            <Ticket aria-hidden="true" />
            <h2>Доступные разделы</h2>
          </div>
          <div className="table" role="table" aria-label="Разграничение интерфейса по ролям">
            <div role="row" className="table-row table-head">
              <span role="columnheader">Раздел</span>
              <span role="columnheader">Доступ</span>
              <span role="columnheader">Статус</span>
            </div>
            <div role="row" className="table-row">
              <span role="cell">Мои заявки</span>
              <span role="cell">Сотрудник</span>
              <span role="cell">{userRoles.has("employee") ? "Доступно" : "Скрыто"}</span>
            </div>
            <div role="row" className="table-row">
              <span role="cell">Назначенные заявки</span>
              <span role="cell">Исполнитель</span>
              <span role="cell">{userRoles.has("executor") ? "Доступно" : "Скрыто"}</span>
            </div>
            <div role="row" className="table-row">
              <span role="cell">Все заявки и назначение</span>
              <span role="cell">Администратор</span>
              <span role="cell">{userRoles.has("admin") ? "Доступно" : "Скрыто"}</span>
            </div>
            <div role="row" className="table-row">
              <span role="cell">Отчеты руководителя</span>
              <span role="cell">Руководитель</span>
              <span role="cell">Демонстрационный плюс</span>
            </div>
          </div>
        </section>

        {userRoles.has("admin") && (
          <section className="panel" id="admin">
            <div className="panel-title">
              <UserCog aria-hidden="true" />
              <h2>Административный доступ</h2>
            </div>
            <p>
              API `/admin/users` доступен только пользователю с ролью администратора. Полноценное управление
              пользователями остается демонстрационным плюсом.
            </p>
          </section>
        )}
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
