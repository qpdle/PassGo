
import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, NavLink, Route, Routes, Link } from 'react-router-dom';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import { getHealth, getDemoEvents } from './requests';
import './style.css';

const Scanner = React.lazy(() => import('./Scanner'));
const client = new QueryClient({ defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } } });
const menu = [['/', 'Мероприятия'], ['/my-tickets', 'Мои билеты'], ['/organizer', 'Организатор'], ['/scanner', 'Проверка билетов'], ['/connection', 'Связь с сервером']];

function Connection() {
  const health = useQuery({ queryKey: ['health'], queryFn: getHealth });
  return <section className="panel"><h2>Связь с сервером</h2>
    {health.isPending ? <p role="status">Проверяем соединение…</p> : health.isError ? <p role="alert">{health.error.message}</p> : <p role="status" className="success">Сервер и база данных доступны. Ответ: {health.data.status}</p>}
    <button disabled={health.isFetching} onClick={() => void health.refetch()}>{health.isFetching ? 'Проверяем…' : 'Проверить ещё раз'}</button>
  </section>;
}

function Events() {
  const query = useQuery({ queryKey: ['demo-events'], queryFn: getDemoEvents });
  return <><div className="hero"><span>PassGo</span><h1>Мероприятия ближе</h1><p>Программа, регистрация и билет в одном месте.</p></div>
    <section className="panel"><h2>Мероприятия</h2><p className="muted">{query.data?.disabled ? "Тестовый каталог на общем стенде отключён. Связь с сервером можно проверить в меню." : "Тестовый список с сервера. Регистрация пока недоступна."}</p>
      {query.isPending && <p role="status">Загружаем мероприятия…</p>}
      {query.isError && <div role="alert"><p>{query.error.message}</p><button onClick={() => void query.refetch()}>Повторить загрузку</button></div>}
      {query.data && (query.data.results.length ? query.data.results.map(event => <article key={event.id} className="event"><span className="badge">Демонстрационный пример</span><h3>{event.title}</h3><p>{event.description}</p><p className="muted">Лимит: {event.capacity} участников</p></article>) : <p>Пока нет мероприятий.</p>)}
    </section></>;
}

function Placeholder({ title, text }: { title: string; text: string }) {
  return <section className="panel"><h1>{title}</h1><p>{text}</p><p className="muted">Раздел подготовлен для следующего этапа разработки.</p><Link to="/">К мероприятиям</Link></section>;
}

function App() { return <><header><Link className="brand" to="/">PassGo</Link><span>Управление мероприятиями</span></header><div className="layout"><nav aria-label="Основное меню">{menu.map(([to,text]) => <NavLink end={to === '/'} key={to} to={to}>{text}</NavLink>)}</nav><main><Routes>
  <Route path="/" element={<Events />} />
  <Route path="/connection" element={<Connection />} />
  <Route path="/my-tickets" element={<Placeholder title="Мои билеты" text="Здесь появятся ваши регистрации и электронные билеты." />} />
  <Route path="/organizer" element={<Placeholder title="Кабинет организатора" text="Здесь можно будет создавать мероприятия, назначать помещения и составлять программу." />} />
  <Route path="/scanner" element={<React.Suspense fallback={<p role="status">Загружаем сканер…</p>}><Scanner /></React.Suspense>} />
  <Route path="*" element={<Placeholder title="Страница не найдена" text="Проверьте адрес или вернитесь к мероприятиям." />} />
</Routes></main></div><footer>PassGo · Учебный проект</footer></>; }

ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><QueryClientProvider client={client}><BrowserRouter><App /></BrowserRouter></QueryClientProvider></React.StrictMode>);
