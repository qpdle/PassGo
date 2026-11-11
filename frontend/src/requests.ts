const base = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '');

async function request(path: string, allowMissingDemo = false): Promise<unknown> {
  try {
    const response = await fetch(base + path, { credentials: 'same-origin', signal: AbortSignal.timeout(10000) });
    if (response.status === 404 && allowMissingDemo) return { results: [], disabled: true };
    if (!response.ok) throw new Error('Сервер недоступен. Попробуйте ещё раз.');
    return await response.json();
  } catch {
    throw new Error('Не удалось связаться с сервером. Проверьте соединение и повторите запрос.');
  }
}

export async function getHealth(): Promise<{ status: string }> {
  const data = await request('/health/') as { status?: unknown };
  if (data?.status !== 'ok') throw new Error('Сервер вернул неожиданный ответ.');
  return { status: data.status };
}

type DemoEvent = { id: string; title: string; description: string; capacity: number };
export async function getDemoEvents(): Promise<{ results: DemoEvent[]; disabled: boolean }> {
  const data = await request('/demo/events/', true) as { results?: unknown; disabled?: boolean };
  if (!Array.isArray(data?.results) || !data.results.every(item => typeof item.id === 'string' && typeof item.title === 'string' && typeof item.description === 'string' && typeof item.capacity === 'number')) throw new Error('Не удалось прочитать список мероприятий.');
  return { results: data.results, disabled: data.disabled === true };
}
