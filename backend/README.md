# Backend PassGo

S1-08: минимальный Django + DRF с PostgreSQL в Docker Compose. Единственный маршрут — проверка здоровья. Аккаунты, сессии, админка и бизнес-модели добавляются после определения собственного пользователя в S1-09. Миграции стандартного auth.User на этом этапе не создаются.

## Запуск

1. Запустить Docker Desktop с Linux containers.
2. В корне репозитория скопировать `.env.example` в `.env`.
3. Задать случайный `DJANGO_SECRET_KEY` и `POSTGRES_PASSWORD`. Не публиковать `.env`.
4. Выполнить `docker compose up --build -d` из корня. Первый запуск загружает образы и зависимости. Миграции запускаются перед сервером, база должна пройти healthcheck.
5. Открыть `http://127.0.0.1:18000/api/v1/health/`. Ответ 200: `{"status":"ok"}`. Поддерживается и адрес без завершающего слеша.

Порт задаётся `BACKEND_HOST_PORT`. PostgreSQL не публикуется на порту компьютера. Сервер слушает только localhost. Dockerfile использует Python 3.12, зависимости закреплены в requirements.txt. Образы Python и PostgreSQL закреплены по основной версии, а не digest.

## Проверки и остановка

`docker compose ps` — состояние контейнеров.

`docker compose exec backend python manage.py check` — проверка Django.

`docker compose exec backend python manage.py showmigrations` — список миграций.

`docker compose logs --tail 30 backend` — сообщения запуска.

`docker compose restart` — перезапуск с сохранением данных.

`docker compose down` — удалить контейнеры и сеть, сохранив именованный том. `docker compose up -d` восстанавливает запуск. Не использовать `down -v`, если данные нужно сохранить.

При недоступной базе health возвращает 503 `{"status":"unavailable"}`, без адресов, настроек и текста исключения. Проверка выполняет SELECT 1, а не просто сообщает о работающем процессе.

Это локальная среда разработки с runserver. HTTPS, производственный сервер и DEBUG=false относятся к S1-14. Настройки открытого доступа применяются только к health; перед добавлением приватных маршрутов нужны сессии и разрешения. Формат ошибок бизнес API подключается позднее по S1-06.
