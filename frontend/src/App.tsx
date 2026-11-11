import React from "react";
import { Link, NavLink, Route, Routes } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { AccountMenu, AuthForm, AuthProvider, Protected } from "./auth";
import { getHealth } from "./api";
import { EventList, EventPage } from "./pages";
import { EventEditor } from "./editor";
import { VenuesPage } from "./venues";
import { ErrorBox } from "./ui";
const Scanner = React.lazy(() => import("./Scanner"));
const menu = [
  ["/", "Мероприятия"],
  ["/my-tickets", "Мои билеты"],
  ["/organizer", "Организатор"],
  ["/scanner", "Проверка билетов"],
  ["/connection", "Связь с сервером"],
];
function Connection() {
  const health = useQuery({ queryKey: ["health"], queryFn: getHealth });
  return (
    <section className="panel">
      <h1>Связь с сервером</h1>
      {health.isPending ? (
        <p role="status">Проверяем соединение…</p>
      ) : health.isError ? (
        <ErrorBox error={health.error} />
      ) : (
        <p role="status" className="success">
          Сервер и база данных доступны. Ответ: {health.data.status}
        </p>
      )}
      <button
        disabled={health.isFetching}
        onClick={() => void health.refetch()}
      >
        Проверить ещё раз
      </button>
    </section>
  );
}
function Placeholder({ title, text }: { title: string; text: string }) {
  return (
    <section className="panel">
      <h1>{title}</h1>
      <p>{text}</p>
      <Link to="/">К мероприятиям</Link>
    </section>
  );
}
export default function App() {
  return (
    <AuthProvider>
      <header>
        <Link className="brand" to="/">
          PassGo
        </Link>
        <AccountMenu />
      </header>
      <div className="layout">
        <nav aria-label="Основное меню">
          {menu.map(([to, text]) => (
            <NavLink end={to === "/"} key={to} to={to}>
              {text}
            </NavLink>
          ))}
        </nav>
        <main>
          <Routes>
            <Route path="/" element={<EventList key="public" />} />
            <Route path="/events/:id" element={<EventPage />} />
            <Route path="/login" element={<AuthForm key="login" />} />
            <Route path="/signup" element={<AuthForm key="signup" signup />} />
            <Route
              path="/organizer"
              element={
                <Protected>
                  <EventList key="own" own />
                </Protected>
              }
            />
            <Route
              path="/organizer/events/new"
              element={
                <Protected>
                  <EventEditor key="new" />
                </Protected>
              }
            />
            <Route
              path="/organizer/events/:id"
              element={
                <Protected>
                  <EventEditor />
                </Protected>
              }
            />
            <Route
              path="/organizer/venues"
              element={
                <Protected>
                  <VenuesPage />
                </Protected>
              }
            />
            <Route path="/connection" element={<Connection />} />
            <Route
              path="/my-tickets"
              element={
                <Protected>
                  <Placeholder
                    title="Мои билеты"
                    text="Регистрация на мероприятия и электронные билеты появятся на следующем этапе."
                  />
                </Protected>
              }
            />
            <Route
              path="/scanner"
              element={
                <React.Suspense
                  fallback={<p role="status">Загружаем сканер…</p>}
                >
                  <Scanner />
                </React.Suspense>
              }
            />
            <Route
              path="*"
              element={
                <Placeholder
                  title="Страница не найдена"
                  text="Проверьте адрес или вернитесь к мероприятиям."
                />
              }
            />
          </Routes>
        </main>
      </div>
      <footer>PassGo · Учебный проект</footer>
    </AuthProvider>
  );
}
