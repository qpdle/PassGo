# Проверки проекта

## На компьютере

Запустить контейнеры: `docker compose up --build -d`.

Проверить настройки: `docker compose exec backend python manage.py check`.

Проверить миграции: `docker compose exec backend python manage.py makemigrations --check --dry-run`.

Запустить тесты: `docker compose exec backend python manage.py test accounts events config`.

В папке frontend выполнить `npm ci`, затем `npm run build`. Эта команда проверяет TypeScript и собирает интерфейс.

## В GitHub

Файл .github/workflows/checks.yml запускает эти проверки при отправке изменений и создании pull request. Сервер проверяется с отдельной PostgreSQL базой. Значения пароля и ключа внутри workflow нужны только для временной тестовой среды.

Результат смотрят на вкладке Actions. Пока workflow не опубликован, доступны только локальные проверки.

Проверка оформления Python: установить backend/requirements-dev.txt, затем выполнить в папке backend `python -m ruff format --check .`. Исправление оформления: `python -m ruff format .`. Базовая проверка ошибок: `python -m ruff check --select E9,F63,F7,F82 .`.
