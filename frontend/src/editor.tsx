import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { allPages, api, ApiError } from "./api";
import { useAuth } from "./auth";
import { ErrorBox, LoadState, useAction, useApi } from "./ui";
import {
  dateText,
  statuses,
  utcTime,
  wallTime,
  type EventData,
  type EventRoom,
  type Program,
  type Room,
  type Staff,
  type Venue,
} from "./types";

export function EventEditor() {
  const { id } = useParams();
  const event = useApi<EventData>(`/events/${id}/`, !!id);
  const auth = useAuth();
  if (!id) return <EventForm />;
  return (
    <LoadState query={event}>
      {event.data &&
        (event.data.owner_id === auth.user?.id ? (
          <>
            <EventForm key={id} event={event.data} />
            <EventRoomsEditor event={event.data} />
            <ProgramEditor event={event.data} />
            <StaffEditor event={event.data} />
          </>
        ) : (
          <section className="panel">
            <h1>Нет доступа к редактору</h1>
            <p>Это мероприятие другого организатора.</p>
            <Link to="/organizer">К своим мероприятиям</Link>
          </section>
        ))}
    </LoadState>
  );
}

function EventForm({ event }: { event?: EventData }) {
  const navigate = useNavigate();
  const action = useAction();
  const [title, setTitle] = useState(event?.title || "");
  const [description, setDescription] = useState(event?.description || "");
  const [zone, setZone] = useState(event?.timezone || "Europe/Moscow");
  const [capacity, setCapacity] = useState(event ? String(event.capacity) : "");
  const [start, setStart] = useState(
    event ? wallTime(event.starts_at, event.timezone) : "",
  );
  const [end, setEnd] = useState(
    event ? wallTime(event.ends_at, event.timezone) : "",
  );
  const [opens, setOpens] = useState(
    event ? wallTime(event.registration_opens_at, event.timezone) : "",
  );
  const [closes, setCloses] = useState(
    event ? wallTime(event.registration_closes_at, event.timezone) : "",
  );
  const [notice, setNotice] = useState("");
  const draft = !event || event.status === "draft";
  const editable =
    draft ||
    (event?.status === "published" && Date.parse(event.starts_at) > Date.now());
  const canCancel =
    event &&
    (event.status === "draft" ||
      (event.status === "published" && Date.parse(event.ends_at) > Date.now()));
  return (
    <section className="panel">
      <Link to="/organizer">К своим мероприятиям</Link>
      <h1>{event ? "Редактор мероприятия" : "Новое мероприятие"}</h1>
      {event && (
        <p>
          <span className="badge">{statuses[event.status]}</span>{" "}
          <Link to={`/events/${event.id}`}>Открыть страницу</Link>
        </p>
      )}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          setNotice("");
          void action.run(async () => {
            const data = {
              title,
              description,
              capacity: Number(capacity),
              ...(draft
                ? {
                    timezone: zone,
                    starts_at: utcTime(start, zone),
                    ends_at: utcTime(end, zone),
                    registration_opens_at: utcTime(opens, zone),
                    registration_closes_at: utcTime(closes, zone),
                  }
                : {}),
            };
            const saved = await api<EventData>(
              event ? `/events/${event.id}/` : "/events/",
              event ? "PATCH" : "POST",
              data,
            );
            setNotice("Изменения сохранены.");
            if (!event)
              navigate(`/organizer/events/${saved.id}`, { replace: true });
          });
        }}
      >
        <fieldset disabled={action.pending || !editable}>
          <label>
            Название мероприятия
            <input
              required
              maxLength={200}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </label>
          <label>
            Описание
            <textarea
              maxLength={30000}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </label>
          <label>
            Часовой пояс
            <input
              required
              disabled={!draft}
              maxLength={64}
              value={zone}
              list="timezones"
              onChange={(e) => setZone(e.target.value)}
            />
            <datalist id="timezones">
              <option value="Europe/Moscow" />
              <option value="Asia/Yekaterinburg" />
              <option value="Asia/Novosibirsk" />
              <option value="Asia/Vladivostok" />
            </datalist>
          </label>
          <p className="muted">
            Все даты ниже относятся к этому часовому поясу.
          </p>
          <div className="form-grid">
            <label>
              Начало мероприятия
              <input
                required
                disabled={!draft}
                type="datetime-local"
                value={start}
                onChange={(e) => setStart(e.target.value)}
              />
            </label>
            <label>
              Окончание мероприятия
              <input
                required
                disabled={!draft}
                type="datetime-local"
                value={end}
                onChange={(e) => setEnd(e.target.value)}
              />
            </label>
            <label>
              Открытие регистрации
              <input
                required
                disabled={!draft}
                type="datetime-local"
                value={opens}
                onChange={(e) => setOpens(e.target.value)}
              />
            </label>
            <label>
              Закрытие регистрации
              <input
                required
                disabled={!draft}
                type="datetime-local"
                value={closes}
                onChange={(e) => setCloses(e.target.value)}
              />
            </label>
          </div>
          <label>
            Лимит участников
            <input
              required
              type="number"
              min="1"
              max="2147483647"
              step="1"
              value={capacity}
              onChange={(e) => setCapacity(e.target.value)}
            />
          </label>
          <button type="submit">
            {action.pending ? "Сохраняем…" : "Сохранить мероприятие"}
          </button>
        </fieldset>
      </form>
      <ErrorBox error={action.error} />
      {notice && (
        <p role="status" className="success">
          {notice}
        </p>
      )}
      {event?.status === "draft" && (
        <div className="publish-box">
          <h2>Публикация</h2>
          <p>
            Сначала сохраните форму и назначьте помещения. После публикации даты
            и состав помещений фиксируются.
          </p>
          <button
            disabled={action.pending}
            onClick={() => {
              if (
                window.confirm("Опубликовать сохранённую версию мероприятия?")
              )
                void action.run(async () => {
                  await api(`/events/${event.id}/publish/`, "POST", {});
                  setNotice("Мероприятие опубликовано.");
                });
            }}
          >
            Опубликовать мероприятие
          </button>
        </div>
      )}
      {canCancel && (
        <p className="event-cancel">
          <button
            className="danger"
            disabled={action.pending}
            onClick={() => {
              if (
                window.confirm(
                  "Отменить мероприятие? Вернуть его в черновик будет нельзя.",
                )
              )
                void action.run(async () => {
                  await api(`/events/${event.id}/cancel/`, "POST", {});
                  setNotice("Мероприятие отменено.");
                });
            }}
          >
            Отменить мероприятие
          </button>
        </p>
      )}
      {!editable && (
        <p className="muted">Редактирование этого мероприятия недоступно.</p>
      )}
    </section>
  );
}

function EventRoomsEditor({ event }: { event: EventData }) {
  const client = useQueryClient();
  const assigned = useQuery({
    queryKey: ["api", "event-rooms", event.id],
    queryFn: () => allPages<EventRoom>(`/events/${event.id}/rooms/`),
  });
  const venues = useQuery({
    queryKey: ["api", "venues"],
    queryFn: () => allPages<Venue>("/venues/"),
  });
  const [venue, setVenue] = useState("");
  const [room, setRoom] = useState("");
  const action = useAction();
  const rooms = useQuery({
    queryKey: ["api", "venue-rooms", venue],
    queryFn: () => allPages<Room>(`/venues/${venue}/rooms/`),
    enabled: !!venue,
  });
  const draft = event.status === "draft";
  const availableRooms =
    rooms.data?.filter(
      (r) => !assigned.data?.some((a) => a.room_id === r.id),
    ) || [];
  const selectedRoom = room || assigned.data?.[0]?.room_id || "";
  const selectedAssignment = assigned.data?.find(
    (r) => r.room_id === selectedRoom,
  );
  function addRoom(roomId: string) {
    if (!roomId || assigned.data?.some((r) => r.room_id === roomId)) return;
    void action.run(async () => {
      let saved: EventRoom;
      try {
        saved = await api<EventRoom>(`/events/${event.id}/rooms/`, "POST", {
          room_id: roomId,
        });
      } catch (error) {
        if (
          error instanceof ApiError &&
          error.code === "room_already_assigned"
        ) {
          const current = await allPages<EventRoom>(
            `/events/${event.id}/rooms/`,
          );
          client.setQueryData(["api", "event-rooms", event.id], current);
          return;
        }
        throw error;
      }
      await client.cancelQueries({
        queryKey: ["api", "event-rooms", event.id],
      });
      client.setQueryData<EventRoom[]>(
        ["api", "event-rooms", event.id],
        (current = []) => [
          ...current.filter((item) => item.id !== saved.id),
          saved,
        ],
      );
    });
  }
  return (
    <section className="panel" id="event-rooms">
      <h2>Помещения мероприятия</h2>
      <LoadState query={assigned}>
        {assigned.data?.length === 0 && <p>Помещения пока не назначены.</p>}
        {!draft &&
          assigned.data?.map((r) => (
            <div className="list-row" key={r.id}>
              <span>
                <strong>{r.name_snapshot}</strong> · {r.capacity_snapshot} мест
                <br />
                {r.address_snapshot}
              </span>
              {draft && (
                <button
                  className="danger"
                  disabled={action.pending}
                  onClick={() => {
                    if (window.confirm("Убрать помещение из мероприятия?"))
                      void action.run(async () => {
                        await api(
                          `/events/${event.id}/rooms/${r.id}/`,
                          "DELETE",
                        );
                      });
                  }}
                >
                  Убрать помещение
                </button>
              )}
            </div>
          ))}
        <p>
          Всего мест:{" "}
          {assigned.data?.reduce((n, r) => n + r.capacity_snapshot, 0) || 0};
          лимит мероприятия: {event.capacity}.
        </p>
      </LoadState>
      {draft ? (
        <>
          <p>
            <Link to="/organizer/venues">Создать площадку или помещение</Link>
          </p>
          <p>
            Выберите площадку, затем помещение. Оно сохранится автоматически и
            сразу появится в списке при составлении программы. Можно добавить
            несколько помещений и переключаться между ними в списке.
          </p>
          <LoadState query={venues}>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                addRoom(room);
              }}
            >
              <fieldset disabled={action.pending}>
                <label>
                  Площадка
                  <select
                    required
                    value={venue}
                    onChange={(e) => {
                      setVenue(e.target.value);
                      setRoom("");
                    }}
                  >
                    <option value="">Выберите площадку</option>
                    {venues.data?.map((v) => (
                      <option key={v.id} value={v.id}>
                        {v.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Помещение
                  <select
                    required
                    value={selectedRoom}
                    onChange={(e) => {
                      setRoom(e.target.value);
                      addRoom(e.target.value);
                    }}
                  >
                    <option value="" disabled hidden>
                      Выберите помещение
                    </option>
                    {!!assigned.data?.length && (
                      <optgroup label="Помещения мероприятия">
                        {assigned.data.map((r) => (
                          <option key={r.id} value={r.room_id}>
                            {r.name_snapshot} · {r.capacity_snapshot} мест
                          </option>
                        ))}
                      </optgroup>
                    )}
                    {!!availableRooms.length && (
                      <optgroup label="Добавить к мероприятию">
                        {availableRooms.map((r) => (
                          <option key={r.id} value={r.id}>
                            {r.name} · {r.capacity} мест
                          </option>
                        ))}
                      </optgroup>
                    )}
                  </select>
                </label>
                {selectedAssignment && (
                  <>
                    <p className="muted">
                      {selectedAssignment.address_snapshot}
                    </p>
                    <button
                      type="button"
                      className="danger"
                      onClick={() => {
                        if (window.confirm("Убрать помещение из мероприятия?"))
                          void action.run(async () => {
                            await api(
                              `/events/${event.id}/rooms/${selectedAssignment.id}/`,
                              "DELETE",
                            );
                            client.setQueryData<EventRoom[]>(
                              ["api", "event-rooms", event.id],
                              (current = []) =>
                                current.filter(
                                  (r) => r.id !== selectedAssignment.id,
                                ),
                            );
                            setRoom("");
                          });
                      }}
                    >
                      Убрать помещение
                    </button>
                  </>
                )}
                {venue && (
                  <LoadState query={rooms}>
                    {rooms.data?.length === 0 && (
                      <p>У этой площадки пока нет помещений.</p>
                    )}
                    {!!rooms.data?.length && availableRooms.length === 0 && (
                      <p>
                        Все помещения этой площадки уже добавлены к мероприятию.
                      </p>
                    )}
                  </LoadState>
                )}
                {action.pending && <p role="status">Сохраняем помещение…</p>}
                {!!action.error && room && (
                  <button type="submit">Повторить сохранение</button>
                )}
              </fieldset>
            </form>
          </LoadState>
        </>
      ) : (
        <p className="muted">
          Состав помещений зафиксирован. Изменение справочника не меняет
          опубликованное мероприятие.
        </p>
      )}
      <ErrorBox error={action.error} />
    </section>
  );
}

function ProgramEditor({ event }: { event: EventData }) {
  const program = useQuery({
    queryKey: ["api", "event-program", event.id],
    queryFn: () => allPages<Program>(`/events/${event.id}/program/`),
  });
  const rooms = useQuery({
    queryKey: ["api", "event-rooms", event.id],
    queryFn: () => allPages<EventRoom>(`/events/${event.id}/rooms/`),
  });
  const [edit, setEdit] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [speaker, setSpeaker] = useState("");
  const [description, setDescription] = useState("");
  const [room, setRoom] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const action = useAction();
  const editable =
    event.status === "draft" ||
    (event.status === "published" && Date.parse(event.starts_at) > Date.now());
  function reset() {
    setEdit(null);
    setTitle("");
    setSpeaker("");
    setDescription("");
    setRoom("");
    setStart("");
    setEnd("");
  }
  return (
    <section className="panel">
      <h2>Программа</h2>
      <p className="muted">
        Часовой пояс: {event.timezone}. В одном помещении выступления не должны
        пересекаться.
      </p>
      <LoadState query={program}>
        {program.data?.length === 0 && <p>Выступлений пока нет.</p>}
        {program.data?.map((p) => (
          <article key={p.id} className="event">
            <h3>{p.title}</h3>
            <p>
              {dateText(p.starts_at, event.timezone)} —{" "}
              {dateText(p.ends_at, event.timezone)}
            </p>
            <p>
              {rooms.data?.find((r) => r.id === p.event_room_id)?.name_snapshot}{" "}
              · {p.speaker}
            </p>
            {editable && (
              <div className="controls">
                <button
                  className="secondary"
                  onClick={() => {
                    setEdit(p.id);
                    setTitle(p.title);
                    setSpeaker(p.speaker);
                    setDescription(p.description);
                    setRoom(p.event_room_id);
                    setStart(wallTime(p.starts_at, event.timezone));
                    setEnd(wallTime(p.ends_at, event.timezone));
                  }}
                >
                  Изменить выступление
                </button>
                <button
                  className="danger"
                  disabled={action.pending}
                  onClick={() => {
                    if (window.confirm(`Удалить выступление «${p.title}»?`))
                      void action.run(async () => {
                        await api(
                          `/events/${event.id}/program/${p.id}/`,
                          "DELETE",
                        );
                        if (edit === p.id) reset();
                      });
                  }}
                >
                  Удалить выступление
                </button>
              </div>
            )}
          </article>
        ))}
      </LoadState>
      {editable && (
        <LoadState query={rooms}>
          <h3>{edit ? "Изменить выступление" : "Добавить выступление"}</h3>
          {rooms.data?.length === 0 && (
            <p role="status">
              Для программы сначала добавьте хотя бы одно помещение к
              мероприятию. <a href="#event-rooms">Перейти к выбору помещений</a>
            </p>
          )}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void action.run(async () => {
                await api(
                  `/events/${event.id}/program/${edit ? edit + "/" : ""}`,
                  edit ? "PATCH" : "POST",
                  {
                    title,
                    description,
                    speaker,
                    event_room_id: room,
                    starts_at: utcTime(start, event.timezone),
                    ends_at: utcTime(end, event.timezone),
                  },
                );
                reset();
              });
            }}
          >
            <fieldset disabled={action.pending}>
              <label>
                Название выступления
                <input
                  required
                  maxLength={200}
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                />
              </label>
              <label>
                Описание выступления
                <textarea
                  maxLength={30000}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
              </label>
              <label>
                Спикер
                <input
                  maxLength={200}
                  value={speaker}
                  onChange={(e) => setSpeaker(e.target.value)}
                />
              </label>
              <label>
                Помещение выступления
                <select
                  required
                  value={room}
                  onChange={(e) => setRoom(e.target.value)}
                >
                  <option value="" disabled hidden>
                    {rooms.data?.length
                      ? "Выберите помещение"
                      : "Сначала добавьте помещение к мероприятию"}
                  </option>
                  {rooms.data?.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.name_snapshot}
                    </option>
                  ))}
                </select>
              </label>
              <div className="form-grid">
                <label>
                  Начало выступления
                  <input
                    required
                    type="datetime-local"
                    value={start}
                    onChange={(e) => setStart(e.target.value)}
                  />
                </label>
                <label>
                  Конец выступления
                  <input
                    required
                    type="datetime-local"
                    value={end}
                    onChange={(e) => setEnd(e.target.value)}
                  />
                </label>
              </div>
              <div className="controls">
                <button
                  type="submit"
                  disabled={!rooms.data?.some((r) => r.id === room)}
                >
                  Сохранить выступление
                </button>
                {edit && (
                  <button type="button" className="secondary" onClick={reset}>
                    Отмена
                  </button>
                )}
              </div>
            </fieldset>
          </form>
        </LoadState>
      )}
      <ErrorBox error={action.error} />
    </section>
  );
}

function StaffEditor({ event }: { event: EventData }) {
  const staff = useQuery({
    queryKey: ["api", "staff", event.id],
    queryFn: () => allPages<Staff>(`/events/${event.id}/staff/`),
  });
  const [email, setEmail] = useState("");
  const action = useAction();
  const editable =
    event.status === "draft" ||
    (event.status === "published" && Date.parse(event.ends_at) > Date.now());
  return (
    <section className="panel">
      <h2>Сотрудники</h2>
      <p>
        Сотрудник назначается по email существующего аккаунта. Редактирование
        мероприятия остаётся у организатора.
      </p>
      <LoadState query={staff}>
        {staff.data?.length === 0 && <p>Сотрудников пока нет.</p>}
        {staff.data?.map((s) => (
          <div className="list-row" key={s.id}>
            <span>
              {s.user.full_name}
              <br />
              {s.user.email}
            </span>
            {editable && (
              <button
                className="danger"
                disabled={action.pending}
                onClick={() => {
                  if (window.confirm("Снять назначение сотрудника?"))
                    void action.run(async () => {
                      await api(`/events/${event.id}/staff/${s.id}/`, "DELETE");
                    });
                }}
              >
                Снять назначение
              </button>
            )}
          </div>
        ))}
      </LoadState>
      {editable && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void action.run(async () => {
              await api(`/events/${event.id}/staff/`, "POST", { email });
              setEmail("");
            });
          }}
        >
          <fieldset disabled={action.pending}>
            <label>
              Email сотрудника
              <input
                required
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </label>
            <button type="submit">Назначить сотрудника</button>
          </fieldset>
        </form>
      )}
      <ErrorBox error={action.error} />
    </section>
  );
}
