import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { allPages, type Page } from "./api";
import { useApi, LoadState, Pager } from "./ui";
import {
  dateText,
  statuses,
  type EventData,
  type EventRoom,
  type Program,
} from "./types";
import { useAuth } from "./auth";

export function EventList({ own = false }: { own?: boolean }) {
  const [page, setPage] = useState(1);
  const query = useApi<Page<EventData>>(
    `${own ? "/me/events/" : "/events/"}?page=${page}`,
  );
  return (
    <>
      <div className="hero">
        <h1>{own ? "Кабинет организатора" : "Мероприятия ближе"}</h1>
        <p>
          {own
            ? "Ваши мероприятия и программа."
            : "Выберите мероприятие и посмотрите программу."}
        </p>
        {own && (
          <Link className="button light" to="/organizer/events/new">
            Создать мероприятие
          </Link>
        )}
      </div>
      {own && (
        <p>
          <Link to="/organizer/venues">Мои площадки и помещения</Link>
        </p>
      )}
      <section className="panel">
        <h2>{own ? "Мои мероприятия" : "Мероприятия"}</h2>
        <LoadState query={query}>
          {query.data?.results.length === 0 && (
            <p>
              {own
                ? "У вас пока нет мероприятий. Создайте первое."
                : "Опубликованных мероприятий пока нет."}
            </p>
          )}
          {query.data?.results.map((e) => (
            <article className="event" key={e.id}>
              <span className="badge">{statuses[e.status]}</span>
              <h3>
                <Link
                  to={own ? `/organizer/events/${e.id}` : `/events/${e.id}`}
                >
                  {e.title}
                </Link>
              </h3>
              <p>
                {dateText(e.starts_at, e.timezone)} · {e.timezone}
              </p>
              <p className="description preview">{e.description}</p>
              <div className="controls">
                <Link to={`/events/${e.id}`}>
                  {e.status === "draft" ? "Предпросмотр" : "Открыть страницу"}
                </Link>
                {own && (
                  <Link to={`/organizer/events/${e.id}`}>Редактировать</Link>
                )}
              </div>
            </article>
          ))}
          <Pager page={page} count={query.data?.count || 0} setPage={setPage} />
        </LoadState>
      </section>
    </>
  );
}

export function EventPage() {
  const { id } = useParams();
  const auth = useAuth();
  const event = useApi<EventData>(`/events/${id}/`);
  const rooms = useQuery({
    queryKey: ["api", "public-rooms", id],
    queryFn: () => allPages<EventRoom>(`/events/${id}/rooms/`),
  });
  const program = useQuery({
    queryKey: ["api", "public-program", id],
    queryFn: () => allPages<Program>(`/events/${id}/program/`),
  });
  const data = event.data;
  return (
    <section className="panel">
      <LoadState query={event}>
        {data && (
          <>
            <span className="badge">{statuses[data.status]}</span>
            <h1>{data.title}</h1>
            <p>
              {dateText(data.starts_at, data.timezone)} —{" "}
              {dateText(data.ends_at, data.timezone)}
            </p>
            <p className="muted">
              Часовой пояс: {data.timezone} · Вместимость: {data.capacity}
            </p>
            <p className="description">
              {data.description || "Описание пока не добавлено."}
            </p>
            {data.owner_id === auth.user?.id && (
              <Link to={`/organizer/events/${data.id}`}>
                Редактировать мероприятие
              </Link>
            )}
            <h2>Где проходит</h2>
            <LoadState query={rooms}>
              {rooms.data?.length === 0 && <p>Помещения пока не выбраны.</p>}
              {rooms.data?.map((r) => (
                <article className="event" key={r.id}>
                  <h3>{r.name_snapshot}</h3>
                  <p>{r.address_snapshot}</p>
                  <p className="muted">Вместимость: {r.capacity_snapshot}</p>
                </article>
              ))}
            </LoadState>
            <h2>Программа</h2>
            <LoadState query={program}>
              {program.data?.length === 0 && (
                <p>Программа пока не добавлена.</p>
              )}
              {program.data?.map((p) => (
                <article className="event" key={p.id}>
                  <p>
                    {dateText(p.starts_at, data.timezone)} —{" "}
                    {dateText(p.ends_at, data.timezone)}
                  </p>
                  <h3>{p.title}</h3>
                  <p>
                    {rooms.data?.find((r) => r.id === p.event_room_id)
                      ?.name_snapshot || "Помещение"}
                  </p>
                  {p.speaker && <p>Спикер: {p.speaker}</p>}
                  <p className="description">{p.description}</p>
                </article>
              ))}
            </LoadState>
          </>
        )}
      </LoadState>
    </section>
  );
}
