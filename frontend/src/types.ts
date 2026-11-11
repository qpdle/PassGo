export type User = { id: string; email: string; full_name: string };
export type EventData = {
  id: string;
  owner_id: string;
  title: string;
  description: string;
  timezone: string;
  status: "draft" | "published" | "cancelled" | "completed";
  capacity: number;
  starts_at: string;
  ends_at: string;
  registration_opens_at: string;
  registration_closes_at: string;
};
export type Venue = { id: string; name: string; address: string };
export type Room = {
  id: string;
  venue_id: string;
  name: string;
  capacity: number;
};
export type EventRoom = {
  id: string;
  room_id: string;
  name_snapshot: string;
  address_snapshot: string;
  capacity_snapshot: number;
};
export type Program = {
  id: string;
  event_room_id: string;
  title: string;
  description: string;
  speaker: string;
  starts_at: string;
  ends_at: string;
};
export type Staff = { id: string; user: User };
export const statuses: Record<string, string> = {
  draft: "Черновик",
  published: "Опубликовано",
  cancelled: "Отменено",
  completed: "Завершено",
};
export const dateText = (value: string, zone: string) =>
  new Intl.DateTimeFormat("ru-RU", {
    timeZone: zone,
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
export function wallTime(value: string, zone: string) {
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: zone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(new Date(value));
  const p = Object.fromEntries(parts.map((x) => [x.type, x.value]));
  return `${p.year}-${p.month}-${p.day}T${p.hour}:${p.minute}`;
}
export function utcTime(value: string, zone: string) {
  if (!value) throw new Error("Заполните дату и время.");
  const target = Date.parse(value + "Z");
  if (!Number.isFinite(target)) throw new Error("Проверьте дату и время.");
  let instant = target;
  for (let i = 0; i < 4; i++) {
    const local = Date.parse(
      wallTime(new Date(instant).toISOString(), zone) + "Z",
    );
    instant += target - local;
  }
  if (wallTime(new Date(instant).toISOString(), zone) !== value)
    throw new Error("Такого времени нет в выбранном часовом поясе.");
  return new Date(instant).toISOString();
}
