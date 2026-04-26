import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  ClipboardList,
  Database,
  KeyRound,
  LogOut,
  Play,
  RefreshCw,
  Send,
  Server,
  ShieldCheck,
  Ticket,
  UserCheck,
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

const statusLabels = {
  created: "Создана",
  assigned: "Назначена",
  in_progress: "В работе",
  completed: "Выполнена",
  closed: "Закрыта",
};

const priorityLabels = {
  low: "Низкий",
  normal: "Обычный",
  high: "Высокий",
  critical: "Критический",
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
  const [categories, setCategories] = useState([]);
  const [statuses, setStatuses] = useState([]);
  const [users, setUsers] = useState([]);
  const [tickets, setTickets] = useState([]);
  const [selectedTicketId, setSelectedTicketId] = useState(null);
  const [filters, setFilters] = useState({ status_code: "", category_id: "", assignee_id: "", date_from: "", date_to: "" });
  const [ticketError, setTicketError] = useState("");
  const [ticketMessage, setTicketMessage] = useState("");
  const [isTicketsLoading, setIsTicketsLoading] = useState(false);

  const userRoles = useMemo(() => new Set(user?.roles || []), [user]);
  const canUseTickets = userRoles.has("employee") || userRoles.has("executor") || userRoles.has("admin");
  const executors = users.filter((item) => item.roles.includes("executor"));
  const selectedTicket = tickets.find((ticket) => ticket.id === selectedTicketId) || tickets[0] || null;

  async function apiFetch(path, options = {}) {
    const response = await fetch(`${apiBaseUrl}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(options.headers || {}),
      },
    });

    if (!response.ok) {
      let message = "Запрос не выполнен";
      try {
        const data = await response.json();
        message = data.detail || message;
      } catch {
        message = response.statusText || message;
      }
      throw new Error(message);
    }

    if (response.status === 204) {
      return null;
    }
    return response.json();
  }

  async function loadTickets() {
    if (!token || !canUseTickets) {
      setTickets([]);
      return;
    }

    setIsTicketsLoading(true);
    setTicketError("");
    try {
      const search = new URLSearchParams();
      Object.entries(filters).forEach(([key, value]) => {
        if (value) {
          search.set(key, value);
        }
      });
      const data = await apiFetch(`/tickets${search.toString() ? `?${search}` : ""}`);
      setTickets(data);
      setSelectedTicketId((current) => (data.some((ticket) => ticket.id === current) ? current : data[0]?.id || null));
    } catch (error) {
      setTicketError(error.message);
    } finally {
      setIsTicketsLoading(false);
    }
  }

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
        const data = await apiFetch("/auth/me");
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

  useEffect(() => {
    let cancelled = false;

    async function loadDictionaries() {
      if (!token || !canUseTickets) {
        setCategories([]);
        setStatuses([]);
        setUsers([]);
        return;
      }

      try {
        const [categoryData, statusData, userData] = await Promise.all([
          apiFetch("/ticket-categories"),
          apiFetch("/ticket-statuses"),
          userRoles.has("admin") ? apiFetch("/admin/users") : Promise.resolve([]),
        ]);
        if (!cancelled) {
          setCategories(categoryData);
          setStatuses(statusData);
          setUsers(userData);
        }
      } catch (error) {
        if (!cancelled) {
          setTicketError(error.message);
        }
      }
    }

    loadDictionaries();

    return () => {
      cancelled = true;
    };
  }, [token, user?.id]);

  useEffect(() => {
    loadTickets();
  }, [token, user?.id, filters.status_code, filters.category_id, filters.assignee_id, filters.date_from, filters.date_to]);

  const healthText =
    health.status === "ok"
      ? "API и база данных доступны"
      : health.status === "loading"
        ? "Проверка соединения"
        : "Нет соединения с API";

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
    setTickets([]);
    setAuthError("");
  }

  async function handleCreateTicket(event) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    setTicketError("");
    setTicketMessage("");

    try {
      const ticket = await apiFetch("/tickets", {
        method: "POST",
        body: JSON.stringify({
          title: formData.get("title"),
          description: formData.get("description"),
          category_id: Number(formData.get("category_id")),
          priority: formData.get("priority"),
        }),
      });
      setTicketMessage("Заявка создана");
      setSelectedTicketId(ticket.id);
      event.currentTarget.reset();
      await loadTickets();
    } catch (error) {
      setTicketError(error.message);
    }
  }

  async function handleAssignTicket(event) {
    event.preventDefault();
    if (!selectedTicket) {
      return;
    }
    const formData = new FormData(event.currentTarget);
    await runTicketAction(() =>
      apiFetch(`/tickets/${selectedTicket.id}/assign`, {
        method: "PATCH",
        body: JSON.stringify({ assignee_id: Number(formData.get("assignee_id")) }),
      }),
    );
  }

  async function handleStatusChange(statusCode) {
    if (!selectedTicket) {
      return;
    }
    await runTicketAction(() =>
      apiFetch(`/tickets/${selectedTicket.id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status_code: statusCode }),
      }),
    );
  }

  async function runTicketAction(action) {
    setTicketError("");
    setTicketMessage("");
    try {
      const ticket = await action();
      setTicketMessage("Заявка обновлена");
      setSelectedTicketId(ticket.id);
      await loadTickets();
    } catch (error) {
      setTicketError(error.message);
    }
  }

  function updateFilter(key, value) {
    setFilters((current) => ({ ...current, [key]: value }));
  }

  function canMoveTo(statusCode) {
    if (!selectedTicket) {
      return false;
    }
    if (statusCode === "in_progress") {
      return userRoles.has("executor") && selectedTicket.assignee_id === user.id && selectedTicket.status_code === "assigned";
    }
    if (statusCode === "completed") {
      return userRoles.has("executor") && selectedTicket.assignee_id === user.id && selectedTicket.status_code === "in_progress";
    }
    if (statusCode === "closed") {
      return selectedTicket.created_by_id === user.id && selectedTicket.status_code === "completed";
    }
    return false;
  }

  return (
    <main className="app-shell">
      <aside className="sidebar" aria-label="Основная навигация">
        <div className="brand">
          <Ticket aria-hidden="true" />
          <span>DevOps Ticket System</span>
        </div>
        <nav className="nav">
          <a href="#overview" className="nav-link active">Обзор</a>
          <a href="#auth" className="nav-link">Авторизация</a>
          {canUseTickets && <a href="#tickets" className="nav-link">Заявки</a>}
          {userRoles.has("admin") && <a href="#admin" className="nav-link">Пользователи</a>}
        </nav>
      </aside>

      <section className="workspace" id="overview">
        <header className="topbar">
          <div>
            <p className="eyebrow">Итерация 3</p>
            <h1>Жизненный цикл заявок</h1>
          </div>
          <div className={`health ${health.status}`}>
            <Activity aria-hidden="true" />
            <span>{healthText}</span>
          </div>
        </header>

        <section className="status-grid" aria-label="Статус реализации">
          <article className="status-card">
            <Server aria-hidden="true" />
            <h2>Tickets API</h2>
            <p>Создание, просмотр, назначение, фильтры и смена статусов доступны через защищенные endpoint.</p>
          </article>
          <article className="status-card">
            <Database aria-hidden="true" />
            <h2>Справочники</h2>
            <p>Категории и статусы создаются миграцией, без отдельного административного UI.</p>
          </article>
          <article className="status-card">
            <ShieldCheck aria-hidden="true" />
            <h2>RBAC</h2>
            <p>Сотрудник видит свои заявки, исполнитель назначенные, администратор весь список.</p>
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
                    <span className="role-badge" key={role}>{roleLabels[role] || role}</span>
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

        {canUseTickets && (
          <section className="ticket-workspace" id="tickets">
            {userRoles.has("employee") && (
              <article className="panel">
                <div className="panel-title">
                  <Send aria-hidden="true" />
                  <h2>Новая заявка</h2>
                </div>
                <p className="warning-text">
                  Не указывайте ФИО пациентов, номера медицинских карт, диагнозы и другие медицинские данные.
                </p>
                <form className="ticket-form" onSubmit={handleCreateTicket}>
                  <label>
                    <span>Тема</span>
                    <input name="title" minLength="3" maxLength="180" required />
                  </label>
                  <label>
                    <span>Категория</span>
                    <select name="category_id" required defaultValue="">
                      <option value="" disabled>Выберите категорию</option>
                      {categories.map((category) => (
                        <option value={category.id} key={category.id}>{category.name}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    <span>Приоритет</span>
                    <select name="priority" defaultValue="normal">
                      {Object.entries(priorityLabels).map(([value, label]) => (
                        <option value={value} key={value}>{label}</option>
                      ))}
                    </select>
                  </label>
                  <label className="wide-field">
                    <span>Описание</span>
                    <textarea name="description" minLength="10" maxLength="4000" rows="5" required />
                  </label>
                  <button className="button" type="submit">
                    <Send aria-hidden="true" />
                    <span>Создать</span>
                  </button>
                </form>
              </article>
            )}

            <article className="panel">
              <div className="panel-title split-title">
                <span>
                  <ClipboardList aria-hidden="true" />
                  <h2>Заявки</h2>
                </span>
                <button className="icon-button" type="button" onClick={loadTickets} aria-label="Обновить заявки">
                  <RefreshCw aria-hidden="true" />
                </button>
              </div>

              <div className="filters">
                <select value={filters.status_code} onChange={(event) => updateFilter("status_code", event.target.value)}>
                  <option value="">Все статусы</option>
                  {statuses.map((item) => (
                    <option value={item.code} key={item.code}>{item.name}</option>
                  ))}
                </select>
                <select value={filters.category_id} onChange={(event) => updateFilter("category_id", event.target.value)}>
                  <option value="">Все категории</option>
                  {categories.map((item) => (
                    <option value={item.id} key={item.id}>{item.name}</option>
                  ))}
                </select>
                {userRoles.has("admin") && (
                  <select value={filters.assignee_id} onChange={(event) => updateFilter("assignee_id", event.target.value)}>
                    <option value="">Все исполнители</option>
                    {executors.map((item) => (
                      <option value={item.id} key={item.id}>{item.full_name}</option>
                    ))}
                  </select>
                )}
                <input type="date" value={filters.date_from} onChange={(event) => updateFilter("date_from", event.target.value)} aria-label="Дата от" />
                <input type="date" value={filters.date_to} onChange={(event) => updateFilter("date_to", event.target.value)} aria-label="Дата до" />
              </div>

              {ticketError && <p className="form-error">{ticketError}</p>}
              {ticketMessage && <p className="form-success">{ticketMessage}</p>}

              <div className="ticket-list">
                {isTicketsLoading && <p>Загрузка заявок</p>}
                {!isTicketsLoading && tickets.length === 0 && <p>Заявок по текущим условиям нет.</p>}
                {tickets.map((ticket) => (
                  <button
                    className={`ticket-row ${selectedTicket?.id === ticket.id ? "selected" : ""}`}
                    type="button"
                    key={ticket.id}
                    onClick={() => setSelectedTicketId(ticket.id)}
                  >
                    <span>
                      <strong>#{ticket.id} {ticket.title}</strong>
                      <small>{ticket.category_name} · {priorityLabels[ticket.priority]}</small>
                    </span>
                    <span className={`status-pill ${ticket.status_code}`}>{statusLabels[ticket.status_code] || ticket.status_name}</span>
                  </button>
                ))}
              </div>
            </article>

            <article className="panel">
              <div className="panel-title">
                <Ticket aria-hidden="true" />
                <h2>Карточка заявки</h2>
              </div>
              {selectedTicket ? (
                <div className="ticket-card">
                  <div className="ticket-card-head">
                    <div>
                      <p className="eyebrow">#{selectedTicket.id}</p>
                      <h2>{selectedTicket.title}</h2>
                    </div>
                    <span className={`status-pill ${selectedTicket.status_code}`}>{selectedTicket.status_name}</span>
                  </div>
                  <p>{selectedTicket.description}</p>
                  <dl className="ticket-meta">
                    <div><dt>Категория</dt><dd>{selectedTicket.category_name}</dd></div>
                    <div><dt>Приоритет</dt><dd>{priorityLabels[selectedTicket.priority]}</dd></div>
                    <div><dt>Заявитель</dt><dd>{selectedTicket.created_by_name}</dd></div>
                    <div><dt>Исполнитель</dt><dd>{selectedTicket.assignee_name || "Не назначен"}</dd></div>
                  </dl>

                  {userRoles.has("admin") && (
                    <form className="assign-form" onSubmit={handleAssignTicket}>
                      <select name="assignee_id" defaultValue={selectedTicket.assignee_id || ""} required>
                        <option value="" disabled>Назначить исполнителя</option>
                        {executors.map((item) => (
                          <option value={item.id} key={item.id}>{item.full_name}</option>
                        ))}
                      </select>
                      <button className="button secondary" type="submit">
                        <UserCheck aria-hidden="true" />
                        <span>Назначить</span>
                      </button>
                    </form>
                  )}

                  <div className="actions">
                    <button className="button secondary" type="button" disabled={!canMoveTo("in_progress")} onClick={() => handleStatusChange("in_progress")}>
                      <Play aria-hidden="true" />
                      <span>В работу</span>
                    </button>
                    <button className="button secondary" type="button" disabled={!canMoveTo("completed")} onClick={() => handleStatusChange("completed")}>
                      <ShieldCheck aria-hidden="true" />
                      <span>Выполнена</span>
                    </button>
                    <button className="button secondary" type="button" disabled={!canMoveTo("closed")} onClick={() => handleStatusChange("closed")}>
                      <Ticket aria-hidden="true" />
                      <span>Закрыть</span>
                    </button>
                  </div>
                </div>
              ) : (
                <p>Выберите заявку из списка.</p>
              )}
            </article>
          </section>
        )}

        {userRoles.has("admin") && (
          <section className="panel" id="admin">
            <div className="panel-title">
              <UserCog aria-hidden="true" />
              <h2>Административный доступ</h2>
            </div>
            <p>Администратор видит все заявки, может фильтровать список и назначать активного исполнителя.</p>
          </section>
        )}
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
