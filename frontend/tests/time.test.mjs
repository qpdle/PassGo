import assert from "node:assert/strict";
import test from "node:test";
import { utcTime, wallTime } from "../src/types.ts";

test("Время мероприятия считается в его часовом поясе", () => {
  assert.equal(
    utcTime("2026-12-01T10:00", "Europe/Moscow"),
    "2026-12-01T07:00:00.000Z",
  );
  assert.equal(
    utcTime("2026-12-01T10:00", "Asia/Yekaterinburg"),
    "2026-12-01T05:00:00.000Z",
  );
  assert.equal(
    wallTime("2026-12-01T07:00:00Z", "Europe/Moscow"),
    "2026-12-01T10:00",
  );
});
test("Переход через границу года сохраняет правильную дату UTC", () => {
  assert.equal(
    utcTime("2026-01-01T00:30", "Asia/Vladivostok"),
    "2025-12-31T14:30:00.000Z",
  );
});
test("Неверное и несуществующее местное время отклоняется", () => {
  assert.throws(() => utcTime("2026-03-29T02:30", "Europe/Berlin"));
  assert.throws(() => utcTime("", "Europe/Moscow"));
  assert.throws(() => utcTime("2026-12-01T10:00", "No/Such_Zone"));
});
