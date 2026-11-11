const base = (import.meta.env.VITE_API_BASE_URL || "/api/v1").replace(
  /\/$/,
  "",
);
export class ApiError extends Error {
  code: string;
  status: number;
  fields: Record<string, string[]>;
  constructor(
    message: string,
    code = "network_error",
    status = 0,
    fields = {},
  ) {
    super(message);
    this.code = code;
    this.status = status;
    this.fields = fields;
  }
}
async function send<T>(
  path: string,
  method = "GET",
  data?: unknown,
  csrf?: string,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(base + path, {
      method,
      credentials: "same-origin",
      signal: AbortSignal.timeout(15000),
      headers: {
        Accept: "application/json",
        ...(data !== undefined ? { "Content-Type": "application/json" } : {}),
        ...(csrf ? { "X-CSRFToken": csrf } : {}),
      },
      body: data !== undefined ? JSON.stringify(data) : undefined,
    });
  } catch {
    throw new ApiError(
      "Не удалось связаться с сервером. Проверьте соединение и повторите запрос.",
    );
  }
  if (response.status === 204) return undefined as T;
  if (
    response.status >= 500 &&
    !response.headers.get("Content-Type")?.includes("application/json")
  )
    throw new ApiError(
      "Сервер временно недоступен. Попробуйте ещё раз.",
      "server_error",
      response.status,
    );
  let body;
  try {
    body = await response.json();
  } catch {
    throw new ApiError(
      "Сервер вернул непонятный ответ. Повторите запрос.",
      "invalid_response",
      response.status,
    );
  }
  if (!response.ok) {
    if (response.status === 401 && !path.startsWith("/auth/"))
      window.dispatchEvent(new Event("session-expired"));
    throw new ApiError(
      body.message || "Не удалось выполнить запрос.",
      body.code || "server_error",
      response.status,
      body.field_errors || {},
    );
  }
  return body as T;
}
export async function api<T>(
  path: string,
  method = "GET",
  data?: unknown,
): Promise<T> {
  if (method === "GET") return send<T>(path);
  const csrf = await send<{ csrf_token: string }>("/auth/csrf/");
  return send<T>(path, method, data, csrf.csrf_token);
}
export type Page<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};
export async function allPages<T>(path: string): Promise<T[]> {
  const result: T[] = [];
  for (let page = 1; ; page++) {
    const data = await api<Page<T>>(
      path + (path.includes("?") ? "&" : "?") + `page_size=100&page=${page}`,
    );
    result.push(...data.results);
    if (!data.next) return result;
  }
}
export async function getHealth() {
  const result = await api<{ status: string }>("/health/");
  if (result.status !== "ok") throw new ApiError("Сервер временно недоступен.");
  return result;
}
