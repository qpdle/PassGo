import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { api, ApiError } from "./api";
import { ErrorBox, useAction } from "./ui";
import type { User } from "./types";
const AuthContext = createContext<{
  user: User | null;
  loading: boolean;
  error: unknown;
  retry: () => void;
  changed: (user: User | null) => void;
}>({
  user: null,
  loading: true,
  error: null,
  retry: () => {},
  changed: () => {},
});
export const useAuth = () => useContext(AuthContext);
export function AuthProvider({ children }: { children: ReactNode }) {
  const client = useQueryClient();
  const query = useQuery({
    queryKey: ["me"],
    queryFn: async () => {
      try {
        return await api<User>("/auth/me/");
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) return null;
        throw e;
      }
    },
  });
  function changed(user: User | null) {
    client.removeQueries({ predicate: (query) => query.queryKey[0] !== "me" });
    client.setQueryData(["me"], user);
  }
  useEffect(() => {
    const expire = () => changed(null);
    window.addEventListener("session-expired", expire);
    return () => window.removeEventListener("session-expired", expire);
  }, [client]);
  return (
    <AuthContext.Provider
      value={{
        user: query.data || null,
        loading: query.isPending,
        error: query.error,
        retry: () => void query.refetch(),
        changed,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
export function Protected({ children }: { children: ReactNode }) {
  const auth = useAuth();
  const location = useLocation();
  if (auth.loading) return <p role="status">Проверяем вход…</p>;
  if (auth.error)
    return (
      <>
        <ErrorBox error={auth.error} />
        <button onClick={auth.retry}>Повторить</button>
      </>
    );
  if (!auth.user)
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  return <>{children}</>;
}
export function AccountMenu() {
  const auth = useAuth();
  const action = useAction();
  return (
    <div className="account">
      {auth.user ? (
        <>
          <span>{auth.user.full_name}</span>
          <button
            className="secondary"
            disabled={action.pending}
            onClick={() =>
              void action.run(async () => {
                await api("/auth/logout/", "POST", {});
                auth.changed(null);
              })
            }
          >
            Выйти
          </button>
        </>
      ) : (
        <Link to="/login">Войти</Link>
      )}
      <ErrorBox error={action.error} />
    </div>
  );
}
export function AuthForm({ signup = false }: { signup?: boolean }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const action = useAction();
  const auth = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from =
    typeof location.state?.from === "string" &&
    location.state.from.startsWith("/") &&
    !location.state.from.startsWith("//")
      ? location.state.from
      : "/organizer";
  if (auth.user) return <Navigate to={from} replace />;
  return (
    <section className="panel narrow">
      <h1>{signup ? "Создать аккаунт" : "Вход"}</h1>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void action.run(async () => {
            const user = await api<User>(
              signup ? "/auth/signup/" : "/auth/login/",
              "POST",
              { email, password, ...(signup ? { full_name: name } : {}) },
            );
            setPassword("");
            auth.changed(user);
            navigate(from, { replace: true });
          });
        }}
      >
        <fieldset disabled={action.pending}>
          {signup && (
            <label>
              Имя и фамилия
              <input
                required
                maxLength={150}
                autoComplete="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </label>
          )}
          <label>
            Email
            <input
              required
              type="email"
              maxLength={254}
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </label>
          <label>
            Пароль
            <input
              required
              type="password"
              minLength={signup ? 8 : 1}
              maxLength={128}
              autoComplete={signup ? "new-password" : "current-password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          <ErrorBox error={action.error} />
          <button type="submit">
            {action.pending
              ? "Подождите…"
              : signup
                ? "Создать аккаунт"
                : "Войти"}
          </button>
        </fieldset>
      </form>
      <p>
        {signup ? "Уже есть аккаунт?" : "Нет аккаунта?"}{" "}
        <Link state={{ from }} to={signup ? "/login" : "/signup"}>
          {signup ? "Войти" : "Создать аккаунт"}
        </Link>
      </p>
    </section>
  );
}
