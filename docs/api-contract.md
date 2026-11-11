# Контракт API PassGo

Контракт API. Подготовил Орлов Даниил.
Здесь описаны запросы и ответы API. Работающие и будущие маршруты отмечены отдельно. Основа — сценарии S1-03, модель S1-05 и правила S1-04. Маршруты аккаунтов, мероприятий, площадок, помещений, программы и сотрудников реализованы во втором спринте. Регистрация участников, билеты, вход и статистика пока запланированы.

## Общие правила

Префикс /api/v1. JSON UTF-8; имена snake_case. Идентификаторы bigint в запросах и ответах — десятичные строки. Даты RFC 3339 с часовым поясом; сервер возвращает UTC с Z, интерфейс отображает в timezone события. Окна времени полуоткрытые. Поля записи, не объявленные схемой, отклоняются с 400, серверные id, owner_id, status и отметки времени клиент не задаёт. PATCH принимает только изменяемые поля; пустой PATCH — 400.

Все маршруты кроме файлов CSV имеют завершающий слеш. Клиент сразу использует правильный URL; перенаправление POST для исправления слеша не требуется. Успешные ответы содержат сам объект; 204 не содержит тела. Списки: count, next, previous, results; page от 1, page_size по умолчанию 20, максимум 100. Порядок по умолчанию: события starts_at,id; программа starts_at,id; остальные списки id. next и previous — относительные ссылки или null. Публичный список исключает черновики, но может показывать опубликованные, отменённые и завершённые события. Неизвестные параметры фильтрации — 400.

## Сессии и CSRF

Frontend и API размещаются на одном origin; при локальной работе API проксируется через Vite. Запросы отправляются с credentials: same-origin. Session cookie sessionid — HttpOnly, Secure на HTTPS, SameSite=Lax. Пароль и токен сессии не сохраняются в localStorage. Перед первым изменяющим запросом GET /auth/csrf/ устанавливает csrftoken и возвращает csrf_token. Клиент отправляет его в X-CSRFToken при POST, PATCH, DELETE, включая signup, login и logout. После успешного login токен обновляется: повторить GET /auth/csrf/. Login защищается CSRF отдельно и для анонимного пользователя. GET никогда не меняет бизнес данные.

Требуемое различие: 401 not_authenticated — сессии нет или она истекла; 403 permission_denied — сессия есть, но права отсутствуют; 403 csrf_failed — CSRF не прошёл. Для этого используется адаптер SessionAuthentication с authenticate_header, возвращающим Session realm="PassGo", и единый обработчик ошибок. Стандартный DRF SessionAuthentication без адаптера может отвечать 403 вместо 401: это не считается соответствием контракту. Заголовок Authorization: Session не используется; сессия передаётся cookie. Неверные данные login: 401 invalid_credentials, без уточнения существования email. CSRF проверяется до операции; при его отказе возможен 403 раньше проверки сессии. Настройка Django CSRF_FAILURE_VIEW нужна для единого JSON вне DRF.

## Доступ

public — всем; authenticated — вошедшим; owner — организатору своего события; owner_or_staff — организатору или назначенному сотруднику; venue_owner — владельцу площадки. registration_owner и ticket_owner — только владельцу своего участия или билета. Организатор не получает чужой QR. public_or_owner — опубликованное описание всем, черновик только владельцу. Чужие приватные объекты возвращают 404; запрещённое действие над видимым объектом — 403. Вложенный id обязательно проверяется относительно родительского объекта. is_staff Django не означает сотрудника входа.

## Этапы реализации

Спринт 1: только health в S1-08, начальные модели и миграции в S1-09. Спринт 2: аккаунты, события, площадки, программа, назначения. Спринт 3: регистрации и билеты. Спринт 4: вход. Спринт 5: статистика и CSV. В схеме health помечен implemented, тестовый список — implemented_debug_only, остальные операции — planned. Наличие будущего маршрута в схеме не означает его реализацию. В S1-12 добавлен GET /demo/events/: при DEBUG=true он возвращает вымышленный список, при DEBUG=false — пустой ответ 404. Он не заменяет бизнес API. Health возвращает короткий ответ status, а не общий конверт ошибок; request_id для него пока не реализован.

## Маршруты


| Метод и маршрут | Доступ | Спринт | Назначение |
| --- | --- | --- | --- |
| GET /api/v1/health/ | public | 1 | Проверка сервера |
| GET /api/v1/auth/csrf/ | public | 2 | Получить CSRF токен |
| POST /api/v1/auth/signup/ | public | 2 | Создать аккаунт |
| POST /api/v1/auth/login/ | public | 2 | Открыть сессию |
| POST /api/v1/auth/logout/ | authenticated | 2 | Закрыть сессию |
| GET /api/v1/auth/me/ | authenticated | 2 | Текущий пользователь |
| GET /api/v1/events/ | public | 2 | Публичные мероприятия |
| POST /api/v1/events/ | authenticated | 2 | Создать черновик |
| GET /api/v1/events/{event_id}/ | public_or_owner | 2 | Прочитать мероприятие |
| PATCH /api/v1/events/{event_id}/ | owner | 2 | Изменить разрешённые поля |
| POST /api/v1/events/{event_id}/publish/ | owner | 2 | Опубликовать черновик |
| POST /api/v1/events/{event_id}/cancel/ | owner | 2 | Отменить мероприятие |
| GET /api/v1/me/events/ | authenticated | 2 | Свои мероприятия |
| GET /api/v1/venues/ | authenticated | 2 | Свои площадки |
| POST /api/v1/venues/ | authenticated | 2 | Создать площадку |
| GET /api/v1/venues/{venue_id}/ | venue_owner | 2 | Читать свою площадку |
| PATCH /api/v1/venues/{venue_id}/ | venue_owner | 2 | Изменить свою площадку |
| DELETE /api/v1/venues/{venue_id}/ | venue_owner | 2 | Удалить площадку без помещений |
| GET /api/v1/venues/{venue_id}/rooms/ | venue_owner | 2 | Помещения площадки |
| POST /api/v1/venues/{venue_id}/rooms/ | venue_owner | 2 | Добавить помещение |
| PATCH /api/v1/venues/{venue_id}/rooms/{room_id}/ | venue_owner | 2 | Изменить помещение |
| DELETE /api/v1/venues/{venue_id}/rooms/{room_id}/ | venue_owner | 2 | Удалить неиспользуемое помещение |
| GET /api/v1/events/{event_id}/rooms/ | public_or_owner | 2 | Помещения мероприятия |
| POST /api/v1/events/{event_id}/rooms/ | owner | 2 | Назначить своё помещение |
| DELETE /api/v1/events/{event_id}/rooms/{event_room_id}/ | owner | 2 | Снять назначение в черновике |
| GET /api/v1/events/{event_id}/program/ | public_or_owner | 2 | Программа мероприятия |
| POST /api/v1/events/{event_id}/program/ | owner | 2 | Добавить выступление |
| PATCH /api/v1/events/{event_id}/program/{program_item_id}/ | owner | 2 | Изменить выступление |
| DELETE /api/v1/events/{event_id}/program/{program_item_id}/ | owner | 2 | Удалить выступление |
| GET /api/v1/events/{event_id}/staff/ | owner | 2 | Назначенные сотрудники |
| POST /api/v1/events/{event_id}/staff/ | owner | 2 | Назначить существующего пользователя |
| DELETE /api/v1/events/{event_id}/staff/{staff_id}/ | owner | 2 | Снять назначение |
| POST /api/v1/events/{event_id}/registrations/ | authenticated | 3 | Регистрация на мероприятие |
| POST /api/v1/registrations/{registration_id}/cancel/ | registration_owner | 3 | Отменить своё участие |
| GET /api/v1/me/registrations/ | authenticated | 3 | Свои регистрации |
| GET /api/v1/tickets/{ticket_id}/ | ticket_owner | 3 | Свой билет и токен |
| POST /api/v1/events/{event_id}/check-ins/ | owner_or_staff | 4 | Подтвердить проход |
| GET /api/v1/events/{event_id}/registrations/ | owner | 5 | Участники для организатора |
| GET /api/v1/events/{event_id}/statistics/ | owner | 5 | Статистика |
| GET /api/v1/events/{event_id}/exports/attendees.csv | owner | 5 | Экспорт участников |
| GET /api/v1/events/{event_id}/exports/statistics.csv | owner | 5 | Экспорт статистики |

## Правила операций

Создание события требует всех полей EventInput. В черновике можно менять даты, вместимость и окно регистрации. Начало раньше конца; opens < closes <= starts; timezone — действительное имя IANA. checkin_opens_at вычисляет сервер как starts_at минус 60 минут. При публикации назначено хотя бы одно своё помещение, суммарная вместимость покрывает capacity. Публикация фиксирует снимки помещений. После публикации даты и помещения неизменяемы; описание, название, программа и capacity меняются только до начала. Лимит нельзя уменьшить ниже активных регистраций и увеличить выше суммы вместимостей. Возврат в draft не допускается. Повтор publish уже опубликованного и cancel уже отменённого возвращает 200 с текущим объектом; остальные неверные переходы — 409 invalid_transition. Завершение определяется временем сервера независимо от фоновой задачи.

Назначение комнаты допускается только в черновике. Повтор того же room_id возвращает 409 room_already_assigned. Нельзя снять назначение с выступлениями: 409 room_in_use. Используемое в событиях помещение не удаляется. Программа располагается в интервале события, не пересекается внутри одного event_room_id; конфликт — 409 program_overlap. Соседние интервалы допустимы. Изменение справочника Rooms не меняет опубликованные snapshots. Программа и площадки требуют отдельных экранных запросов; в Event их массивов нет.

Назначение сотрудника по email существующего активного пользователя; пользователь не найден — 404 user_not_found, повтор — 409 staff_already_assigned. Отдельные бизнес роли в User не выдаются. Снятие назначения немедленно запрещает дальнейшее подтверждение входа.

POST регистрации без тела: пользователь берётся из сессии. Создание новой строки — 201; повтор активной регистрации — 200 с теми же id регистрации и билета; повторная активация отменённой — 200 с прежним id регистрации и новым ticket_id. Проверка собственного активного дубля идёт до вместимости, но отменённое или завершённое событие новые регистрации не принимает. Конфликты: sold_out, registration_not_open, event_cancelled, event_completed, already_checked_in. Отмена — 200; повтор отмены — 200. После входа либо начала события — 409 cancellation_not_allowed. Отмена события отменяет регистрации и отзывает билеты, исторические входы сохраняются. Статусы регистрации active/cancelled; билет active/revoked; использованность отражает checked_in_at, отдельного статуса used нет.

Ticket выдаёт сырой token только владельцу при active; revoked возвращает token:null. Нет поля digest/ciphertext/key_version в API. Билет читается отдельно по ticket_id из Registration. Изображение QR строится на клиенте из token; отдельный PDF/почтовый маршрут не входит в MVP. Cache-Control:no-store на ответах auth, регистрации, билета, сканера, статистики и экспорта; токен, пароль и cookie не пишутся в журналы, URL или аналитику. EXAMPLE_TOKEN_NOT_VALID — обозначение в примере, не действующий билет.

POST check-ins — одна атомарная проверка и подтверждение, предварительного успешного GET нет. Тело {"token":"…"}. Первый проход — 201 result:accepted; повтор — 200 result:already_checked_in с id и временем первого входа. Новый CheckIns не создаётся. Сотрудник получает только full_name, без email и токена. Отказы — 409 с code invalid_ticket, revoked_ticket, wrong_event, checkin_not_open, event_cancelled, event_completed. Данные участника при отказе не выдаются; при already_checked_in доступны только уполномоченному сотруднику. Неверная форма запроса — 400; чужое назначение — 403 или 404 по правилам доступа. Неизвестный токен не записывается в ScanAttempts, только результат; request_id не является ключом идемпотентности. Потеря ответа не означает отсутствие входа: повторный POST возвращает фактический результат. При сетевой ошибке клиент не показывает успех.

Статистика: active_registrations считает active; unique_attendees — CheckIns; scan_attempts — все записанные попытки. attendance_rate = unique_attendees / active_registrations * 100 с округлением до 1 знака; при нуле регистраций 0, при отменённом событии null. CSV только организатору: UTF-8 с BOM, разделитель точка с запятой, CRLF, Content-Disposition:attachment. Поля attendees.csv: registration_id,full_name,email,registration_status,checked_in_at. statistics.csv: event_id,active_registrations,unique_attendees,scan_attempts,attendance_rate,calculated_at. null в CSV — пустая ячейка. Поля с кавычками/разделителями экранируются; текст, начинающийся с =,+,-,@, табуляции или возврата каретки, нейтрализуется для таблиц.

## Формат ошибок

Во всех JSON ошибках четыре обязательных поля: code (стабильное значение для программы), message (русский текст для человека), field_errors (словарь массивов сообщений, пустой при отсутствии ошибок полей), request_id (UUID корреляции). Ошибки нескольких полей перечисляются одновременно; общая ошибка формы — ключ non_field_errors. request_id создаёт сервер для каждого запроса и возвращает также в X-Request-ID на всех ответах. Внешний X-Request-ID не принимается как доверенный. Заголовок сохраняется и на ответах без тела. Не раскрывать SQL, traceback, секреты. 429 сопровождается Retry-After. 500 internal_error — общий текст без подробностей. Сетевые ошибки не имеют серверного JSON/request_id: клиент показывает локальный network_error и возможность повтора.

400 validation_error — неверные поля; 401 not_authenticated/invalid_credentials — требуется вход или неверные данные входа; 403 permission_denied/csrf_failed — запрет; 404 not_found/user_not_found — объект отсутствует или скрыт; 409 — нарушение бизнес условия; 429 rate_limited — частота запросов; 500 internal_error — неожиданная ошибка. Единый обработчик покрывает DRF, middleware CSRF, API 404 и 405 method_not_allowed; веб страницы вне /api/v1 в этот контракт не входят.


## Примеры JSON

### Event

```json
{
  "id": "12",
  "title": "Встреча IT сообщества",
  "description": "Доклады и знакомство",
  "timezone": "Europe/Moscow",
  "starts_at": "2026-11-07T07:00:00Z",
  "ends_at": "2026-11-07T15:00:00Z",
  "registration_opens_at": "2026-10-05T00:00:00Z",
  "registration_closes_at": "2026-11-07T07:00:00Z",
  "capacity": 100,
  "status": "published",
  "checkin_opens_at": "2026-11-07T06:00:00Z",
  "owner_id": "1",
  "created_at": "2026-10-05T09:00:00Z",
  "updated_at": "2026-10-06T09:00:00Z",
  "published_at": "2026-10-06T09:00:00Z",
  "cancelled_at": null
}
```

### ProgramItem

```json
{
  "id": "21",
  "event_room_id": "11",
  "title": "Открытие",
  "description": "Знакомство участников",
  "speaker": "Ведущий",
  "starts_at": "2026-11-07T07:00:00Z",
  "ends_at": "2026-11-07T07:30:00Z"
}
```

### Registration

```json
{
  "id": "31",
  "event_id": "12",
  "user_id": "2",
  "status": "active",
  "created_at": "2026-10-14T09:00:00Z",
  "activated_at": "2026-10-14T09:00:00Z",
  "cancelled_at": null,
  "ticket_id": "41",
  "checked_in_at": null
}
```

### Ticket

```json
{
  "id": "41",
  "registration_id": "31",
  "event_id": "12",
  "status": "active",
  "token": "EXAMPLE_TOKEN_NOT_VALID",
  "issued_at": "2026-10-14T09:00:00Z",
  "revoked_at": null,
  "checked_in_at": null
}
```

### CheckIn

```json
{
  "result": "accepted",
  "check_in_id": "51",
  "checked_in_at": "2026-11-07T06:30:00Z",
  "participant": {
    "full_name": "Тестовый участник"
  },
  "request_id": "6b731b3d-a78c-4b07-a1b0-90148e639cd2"
}
```

### Statistics

```json
{
  "event_id": "12",
  "active_registrations": 3,
  "unique_attendees": 2,
  "scan_attempts": 5,
  "attendance_rate": 66.7,
  "calculated_at": "2026-11-07T15:00:00Z"
}
```

### Error

```json
{
  "code": "validation_error",
  "message": "Проверьте заполненные поля.",
  "field_errors": {
    "ends_at": [
      "Окончание должно быть позже начала."
    ]
  },
  "request_id": "6b731b3d-a78c-4b07-a1b0-90148e639cd2"
}
```

### Отказ доступа

HTTP 403

```json
{"code":"permission_denied","message":"Недостаточно прав для этого действия.","field_errors":{},"request_id":"6b731b3d-a78c-4b07-a1b0-90148e639cd2"}
```

## Соответствие макетам S1-10

Публичная страница получает Event, EventRoomPage и ProgramPage. Перед формой участия пользователь входит/создаёт аккаунт: имя и email относятся к User, POST регистрации не принимает их повторно. Кабинет использует /me/registrations/, билет — /tickets/{id}/, панель — /me/events/. Редактору необходимо добавить timezone и период регистрации, учитывать запрет изменения дат и помещений после публикации. Создание должно открывать пустую форму, а не существующий пример. Used у макета билета — только визуальная подпись checked_in_at. Статистика в реализации берётся с сервера. Сканер отправляет token и отображает accepted либо already_checked_in/ошибку. Эти различия нужно учесть при подключении интерфейса к API. Прототип пока не подключён к серверу.

## Проверки при реализации

1. Максим проверяет имена полей, примеры и соответствие своим экранам.
2. Незалогиненный приватный запрос получает 401, чужой приватный объект 404, запрещённое действие 403.
3. Signup/login без CSRF возвращают 403; после login новый токен позволяет выполнить POST.
4. Два запроса регистрации на последнее место оставляют одного победителя. Повтор своей активной регистрации возвращает прежний билет.
5. Два POST прохода дают один CheckIns: 201 accepted и 200 already_checked_in.
6. Ошибки валидации, CSRF, middleware, 404 и 405 имеют общий конверт; 204 не содержит JSON.
7. В примерах и схеме нет реальных секретов; будущие маршруты отмечены planned.

Эти серверные проверки — критерии будущей реализации, а не отчёт о пройденных интеграционных тестах. В S1-06 проверяются структура схемы, ссылки и примеры.

## Основания технических соглашений

DRF Authentication: https://www.django-rest-framework.org/api-guide/authentication/
Django CSRF: https://docs.djangoproject.com/en/5.2/howto/csrf/

## Текущее ограничение отмены

Во втором спринте отмена меняет состояние мероприятия. Регистраций участников и билетов ещё нет. При их добавлении отмена должна в той же транзакции отменять активные регистрации и отзывать билеты, сохраняя историю посещений.
