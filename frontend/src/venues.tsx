import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { allPages, api } from "./api";
import { ErrorBox, LoadState, useAction } from "./ui";
import type { Room, Venue } from "./types";

export function VenuesPage() {
  const venues = useQuery({
    queryKey: ["api", "venues"],
    queryFn: () => allPages<Venue>("/venues/"),
  });
  const [edit, setEdit] = useState<Venue | null>(null);
  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const action = useAction();
  return (
    <>
      <Link to="/organizer">К мероприятиям</Link>
      <section className="panel">
        <h1>Площадки и помещения</h1>
        <h2>{edit ? "Изменить площадку" : "Новая площадка"}</h2>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void action.run(async () => {
              await api(
                edit ? `/venues/${edit.id}/` : "/venues/",
                edit ? "PATCH" : "POST",
                { name, address },
              );
              setEdit(null);
              setName("");
              setAddress("");
            });
          }}
        >
          <fieldset disabled={action.pending}>
            <label>
              Название площадки
              <input
                required
                maxLength={200}
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </label>
            <label>
              Адрес
              <textarea
                required
                maxLength={5000}
                value={address}
                onChange={(e) => setAddress(e.target.value)}
              />
            </label>
            <ErrorBox error={action.error} />
            <div className="controls">
              <button type="submit">Сохранить площадку</button>
              {edit && (
                <button
                  type="button"
                  className="secondary"
                  onClick={() => {
                    setEdit(null);
                    setName("");
                    setAddress("");
                  }}
                >
                  Отмена
                </button>
              )}
            </div>
          </fieldset>
        </form>
      </section>
      <LoadState query={venues}>
        {venues.data?.length === 0 && <p>Площадок пока нет.</p>}
        {venues.data?.map((v) => (
          <VenueCard
            key={v.id}
            venue={v}
            onEdit={() => {
              setEdit(v);
              setName(v.name);
              setAddress(v.address);
              window.scrollTo({ top: 0, behavior: "smooth" });
            }}
          />
        ))}
      </LoadState>
    </>
  );
}

function VenueCard({ venue, onEdit }: { venue: Venue; onEdit: () => void }) {
  const rooms = useQuery({
    queryKey: ["api", "venue-rooms", venue.id],
    queryFn: () => allPages<Room>(`/venues/${venue.id}/rooms/`),
  });
  const [edit, setEdit] = useState<Room | null>(null);
  const [name, setName] = useState("");
  const [capacity, setCapacity] = useState("");
  const action = useAction();
  return (
    <section className="panel">
      <h2>{venue.name}</h2>
      <p>{venue.address}</p>
      <div className="controls">
        <button className="secondary" onClick={onEdit}>
          Изменить площадку
        </button>
        <button
          className="danger"
          disabled={action.pending}
          onClick={() => {
            if (window.confirm("Удалить площадку?"))
              void action.run(async () => {
                await api(`/venues/${venue.id}/`, "DELETE");
              });
          }}
        >
          Удалить площадку
        </button>
      </div>
      <h3>Помещения</h3>
      <LoadState query={rooms}>
        {rooms.data?.length === 0 && <p>Помещений пока нет.</p>}
        {rooms.data?.map((r) => (
          <div className="list-row" key={r.id}>
            <span>
              {r.name} · {r.capacity} мест
            </span>
            <div className="controls">
              <button
                className="secondary"
                onClick={() => {
                  setEdit(r);
                  setName(r.name);
                  setCapacity(String(r.capacity));
                }}
              >
                Изменить помещение
              </button>
              <button
                className="danger"
                disabled={action.pending}
                onClick={() => {
                  if (window.confirm(`Удалить помещение «${r.name}»?`))
                    void action.run(async () => {
                      await api(`/venues/${venue.id}/rooms/${r.id}/`, "DELETE");
                    });
                }}
              >
                Удалить помещение
              </button>
            </div>
          </div>
        ))}
      </LoadState>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void action.run(async () => {
            await api(
              `/venues/${venue.id}/rooms/${edit ? edit.id + "/" : ""}`,
              edit ? "PATCH" : "POST",
              { name, capacity: Number(capacity) },
            );
            setEdit(null);
            setName("");
            setCapacity("");
          });
        }}
      >
        <fieldset disabled={action.pending}>
          <h3>{edit ? "Изменить помещение" : "Добавить помещение"}</h3>
          <label>
            Название помещения
            <input
              required
              maxLength={100}
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </label>
          <label>
            Вместимость
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
          <ErrorBox error={action.error} />
          <div className="controls">
            <button type="submit">Сохранить помещение</button>
            {edit && (
              <button
                type="button"
                className="secondary"
                onClick={() => {
                  setEdit(null);
                  setName("");
                  setCapacity("");
                }}
              >
                Отмена
              </button>
            )}
          </div>
        </fieldset>
      </form>
    </section>
  );
}
