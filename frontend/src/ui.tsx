import { useState, type ReactNode } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError, api } from "./api";
export function useApi<T>(path: string, enabled = true) {
  return useQuery({
    queryKey: ["api", path],
    queryFn: () => api<T>(path),
    enabled,
  });
}
const fieldNames: Record<string, string> = {
  email: "Email",
  password: "Пароль",
  full_name: "Имя",
  title: "Название",
  description: "Описание",
  name: "Название",
  address: "Адрес",
  timezone: "Часовой пояс",
  capacity: "Вместимость",
  starts_at: "Начало",
  ends_at: "Окончание",
  registration_opens_at: "Открытие регистрации",
  registration_closes_at: "Закрытие регистрации",
  event_room_id: "Помещение",
  room_id: "Помещение",
  non_field_errors: "Форма",
  speaker: "Спикер",
};
export function ErrorBox({ error }: { error: unknown }) {
  if (!error) return null;
  return (
    <div role="alert" className="error-box">
      <p>
        {error instanceof Error
          ? error.message
          : "Не удалось выполнить действие."}
      </p>
      {error instanceof ApiError &&
        Object.entries(error.fields).map(([name, texts]) => (
          <p key={name}>
            {fieldNames[name] || name}: {texts.join(" ")}
          </p>
        ))}
    </div>
  );
}
export function LoadState({
  query,
  children,
}: {
  query: {
    isPending: boolean;
    isError: boolean;
    error: unknown;
    refetch: () => unknown;
  };
  children: ReactNode;
}) {
  if (query.isPending) return <p role="status">Загружаем…</p>;
  if (query.isError)
    return (
      <>
        <ErrorBox error={query.error} />
        <button onClick={() => void query.refetch()}>Повторить загрузку</button>
      </>
    );
  return <>{children}</>;
}
export function useAction() {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const client = useQueryClient();
  async function run(action: () => Promise<void>) {
    if (pending) return;
    setPending(true);
    setError(null);
    try {
      await action();
      await client.invalidateQueries({ queryKey: ["api"] });
    } catch (e) {
      setError(e);
    } finally {
      setPending(false);
    }
  }
  return { pending, error, run };
}
export function Pager({
  page,
  count,
  setPage,
}: {
  page: number;
  count: number;
  setPage: (p: number) => void;
}) {
  return count > 20 ? (
    <div className="controls">
      <button disabled={page === 1} onClick={() => setPage(page - 1)}>
        Назад
      </button>
      <span>
        Страница {page} из {Math.ceil(count / 20)}
      </span>
      <button disabled={page * 20 >= count} onClick={() => setPage(page + 1)}>
        Далее
      </button>
    </div>
  ) : null;
}
