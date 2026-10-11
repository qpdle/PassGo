# Модель данных PassGo

Результат S1-05. Основание: правила S1-04 в lifecycle.md. Модель описывает полный MVP; начальные миграции S1-09 реализуют только пользователей, события и площадки. Все идентификаторы — bigint PK, если не указано иное. FK индексируются. Поля обязательны, кроме явно помеченных NULL.

## Пользователи и места

Users: id, email varchar(254), password varchar(128), full_name varchar(150), is_active boolean, is_staff boolean, is_superuser boolean, date_joined timestamptz, last_login timestamptz NULL. Пароли хранятся в стандартном формате Django, без самостоятельного хеширования. Email приводится к trim + lowercase при записи; уникальный индекс lower(email) исключает отличия только в регистре. Используется собственная модель пользователя до первой миграции.

Venues: id, owner_id FK Users PROTECT, name varchar(200), address text, created_at timestamptz. Rooms: id, venue_id FK Venues PROTECT, name varchar(100), capacity integer CHECK > 0. UNIQUE(venue_id, name). Общая вместимость площадки вычисляется по помещениям; вместимость помещения не означает лимит параллельных регистраций на отдельный доклад.

## Событие и программа

Events: id, owner_id FK Users PROTECT, title varchar(200), description text, status varchar(16), timezone varchar(64), starts_at timestamptz, ends_at timestamptz, registration_opens_at timestamptz, registration_closes_at timestamptz, checkin_opens_at timestamptz, capacity integer, created_at timestamptz, updated_at timestamptz, published_at timestamptz NULL, cancelled_at timestamptz NULL.

CHECK: status IN ('draft','published','cancelled','completed'); capacity > 0; starts_at < ends_at; registration_opens_at < registration_closes_at ≤ starts_at; checkin_opens_at < ends_at. IANA timezone проверяется сервером. Индексы: (status, starts_at), (owner_id, created_at). published_at и cancelled_at заполняются при переходе; API не позволяет клиенту задавать их.

EventStaff: id, event_id FK Events PROTECT, user_id FK Users PROTECT, created_at timestamptz. UNIQUE(event_id, user_id). В MVP одна роль сотрудника входа; организатор хранится отдельно в Events. Снять назначение можно удалением EventStaff: старые попытки сохраняют actor_id, а не ссылку на назначение.

EventRooms: id, event_id FK Events PROTECT, room_id FK Rooms PROTECT, name_snapshot varchar(100), address_snapshot text, capacity_snapshot integer CHECK > 0. UNIQUE(event_id, room_id). Снимки фиксируются при публикации. Суммарная вместимость назначенных помещений должна покрывать Events.capacity; проверяется сервисом при публикации.

ProgramItems: id, event_room_id FK EventRooms PROTECT, title varchar(200), description text, speaker varchar(200), starts_at timestamptz, ends_at timestamptz. CHECK starts_at < ends_at. Событие определяется через EventRooms, поэтому отдельного event_id нет и нельзя записать противоречивую пару. Индекс (event_room_id, starts_at).

Начало и конец активности должны находиться внутри времени события. Интервалы [start, end) одного EventRoom не пересекаются, соседние активности допустимы. Сервис блокирует Events перед изменением программы, затем проверяет пересечения. Межтабличные правила нельзя выразить обычным CHECK; прямое редактирование этих объектов в admin отключается либо использует тот же сервис. PostgreSQL exclusion constraint может быть добавлен позднее, если появятся дополнительные пути записи.

## Регистрация и билет

Registrations: id, event_id FK Events PROTECT, user_id FK Users PROTECT, status varchar(16), created_at timestamptz, activated_at timestamptz, cancelled_at timestamptz NULL. CHECK status IN ('active','cancelled'); UNIQUE(event_id, user_id). Индексы (event_id, status), (user_id, created_at). Имя и email участника читаются из Users; в MVP регистрация требует учётной записи.

Tickets: id, registration_id FK Registrations PROTECT, status varchar(16), token_digest char(64), token_ciphertext text, token_key_version varchar(32), issued_at timestamptz, revoked_at timestamptz NULL. CHECK status IN ('active','revoked'). UNIQUE(token_digest). Частичный UNIQUE(registration_id) WHERE status='active'. История отозванных билетов сохраняется.

Токен генерируется криптографическим генератором: 32 случайных байта в base64url. Для поиска хранится SHA-256 digest; для повторного отображения QR владельцу — шифротекст с аутентифицированным шифрованием. Один digest не позволяет восстановить QR. Ключ шифрования хранится в окружении, отдельно от БД и репозитория; token_key_version позволяет выбрать ключ при ротации. При отзыве токена ciphertext можно очистить, поэтому поле допускает NULL только у revoked билета. Токены не пишутся в URL, журналы запросов или ScanAttempts. Потеря ключа означает невозможность повторно показать старые QR; требуется контролируемый перевыпуск, а не восстановление из digest.

## Посещение и попытки

CheckIns: id, registration_id FK Registrations PROTECT UNIQUE, ticket_id FK Tickets PROTECT UNIQUE, actor_id FK Users PROTECT, checked_in_at timestamptz. Уникальность регистрации ограничивает вход даже при выпуске нового билета. Событие определяется через регистрацию. Сервис проверяет, что ticket.registration_id совпадает с registration_id. Записи неизменяемы через бизнес-API.

ScanAttempts: id, event_id FK Events PROTECT, actor_id FK Users PROTECT, ticket_id FK Tickets PROTECT NULL, result varchar(32), attempted_at timestamptz, request_id uuid. Индексы (event_id, attempted_at), (actor_id, attempted_at). result принимает значения из lifecycle.md. Для несуществующего токена ticket_id=NULL; исходный токен не сохраняется. request_id служит корреляции запроса, не ключом идемпотентности. Повторный запрос создаёт новую попытку, но не новое посещение.

## Транзакции и порядок блокировок

Общий порядок: Events → Registrations → Tickets. Массовые операции обрабатывают регистрации по id по возрастанию. Для MVP блокировка строки события сериализует записи в рамках одного события; это простое решение для небольших мероприятий. При росте нагрузки оптимизацию делают отдельно, сохраняя уникальные ограничения.

Регистрация: открыть transaction.atomic; SELECT Events FOR UPDATE; проверить статус, время и число active регистраций; прочитать регистрацию пользователя; при уже active вернуть существующий билет; иначе проверить отсутствие CheckIns и вместимость; создать или активировать регистрацию и выпустить билет; commit. Проверка дубля выполняется до проверки свободных мест, чтобы повтор собственного запроса не превращался в ошибку sold_out. Все операции, влияющие на лимит, включая изменение capacity и отмену, используют ту же блокировку Events.

Вход: предварительно найти билет по digest без раскрытия данных; открыть транзакцию; заблокировать целевое событие, регистрацию и билет в указанном порядке; повторно проверить токен, назначение сотрудника, даты и статусы; проверить существующий CheckIns; создать CheckIns и accepted ScanAttempts; commit. Повторная проверка возвращает already_checked_in. Снятие назначения сотрудника также блокирует Events, поэтому оно согласовано с одновременным входом. Билет чужого события не подтверждается.

Отмена участия: блокировать Events, Registrations и active Tickets; проверить отсутствие CheckIns и now < starts_at; установить cancelled и revoked. Отмена события: блокировать Events; установить cancelled; отменить active регистрации и отозвать active билеты, сохранив CheckIns. Второй конкурентный запрос после ожидания блокировки повторно проверяет изменённое состояние.

Если БД обнаружила нарушение уникальности, транзакция откатывается; сервис повторно читает состояние в новой транзакции и возвращает понятный конфликт либо существующий результат. Продолжать работу внутри повреждённой транзакции нельзя.

## Связи

Users 1 → N Events, Venues, Registrations и EventStaff. Venues 1 → N Rooms. Events 1 → N EventRooms, Registrations, EventStaff и ScanAttempts. Rooms 1 → N EventRooms. EventRooms 1 → N ProgramItems. Registrations 1 → N Tickets и 1 → 0..1 CheckIns. Tickets 1 → 0..1 CheckIns и 1 → N ScanAttempts. Повторное назначение помещения разным событиям допустимо; управление календарём площадки между событиями за пределами MVP.

## Проверки при реализации

1. Миграции на пустой PostgreSQL; email с отличием в регистре отклоняется.
2. Два независимых соединения регистрируются на последнее место; победитель один.
3. Повторный запрос регистрации возвращает ту же запись и active билет.
4. Параллельный вход создаёт одну запись CheckIns и две попытки с разными результатами.
5. Отмена участия одновременно с входом не оставляет противоречивых статусов.
6. Старый токен после отмены и повторной регистрации не действует.
7. Программа не пересекается в одном помещении; соседние интервалы допускаются.
8. Отмена события сохраняет исторические входы и запрещает новые.

Это проект модели, а не отчёт о выполненных миграциях или пройденных тестах. Подтверждение покрытия экранов Максимом и проверки конкурентных запросов остаются задачами приёмки.
