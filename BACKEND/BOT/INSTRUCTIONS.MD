<!-- Руководство к файлу (BACKEND/BOT/INSTRUCTIONS.MD)
Назначение:
- Описывает архитектуру каталога BACKEND/BOT (бот на MAX поверх VKMax BACKEND).
- Объясняет, как устроены run_bot.py, KEYBOARDS, ROUTERS, SERVICES и их связь с FAST_API.
-->

# Руководство к каталогу BACKEND/BOT

## 1. Назначение

Каталог `BACKEND/BOT` содержит слой чат‑бота MAX для VKMax. Бот:

- даёт пользователю вход через чат MAX (команды, кнопки);
- работает поверх существующего HTTP‑слоя `BACKEND/FAST_API` (никакой бизнес‑логики внутри хэндлеров бота);
- вызывает только сервисы/HTTP‑API VKMax и MAX Bot API.

Мини‑аппа (WebApp) живёт отдельно, но бот умеет открывать её через кнопки.

## 2. Структура каталогов

- `confg.py`
  - Класс `BotConfig` и глобальный `config`.
  - Читает из окружения:
    - `VKMAX_BOT_TOKEN` — токен бота MAX;
    - `VKMAX_FASTAPI_BASE_URL` — базовый URL FastAPI VKMax;
    - `VKMAX_BOT_DEBUG` — включает подробное логирование.

- `logging_config.py`
  - Функция `setup_logging(debug: bool)` — настраивает `logging` для бота.
  - Логгер `vkmax.bot` используется во всех модулях бота.

- `run_bot.py`
  - Точка входа бота:
    - вызывает `setup_logging`;
    - создаёт `aiomax.Bot(config.bot_token, ...)`;
    - подключает роутеры из `ROUTERS`;
    - запускает long polling (`bot.run()`).

- `KEYBOARDS/`
  - `__init__.py` — экспортирует публичные билдеры клавиатур.
  - `common.py` — общее главное меню, кнопка открытия мини‑аппы (`WebAppButton`).
  - `convert.py` — клавиатуры выбора формата конвертации.

- `ROUTERS/`
  - `__init__.py` — собирает все роутеры в пакет.
  - `user.py` — приветствие, `/start`, показ главного меню.
  - `system.py` — `/ping`, `/stats` (использует `VkmaxApiClient.get_stats`).
  - `files.py` — `/files` (страница файлов через `/files` FastAPI).
  - `format.py` — `/formats` (список форматов и матрица конвертаций через `/formats` и `/supported-conversions`).
  - `convert.py` — `/convert` (выбор формата) и `/convert_file <file_id> <format>` (создание операции через `/convert`).
  - `download.py` — заглушка `/download` под сценарий скачивания.
  - `auth.py` — команда `/app`, показывающая кнопку открытия мини‑приложения VKMax.

- `SERVICES/`
  - `__init__.py` — экспортирует сервисы бота.
  - `vkmax_api.py` — HTTP‑клиент к `BACKEND/FAST_API` (методы `/stats`, `/formats`, `/supported-conversions`, `/files`, `/convert`).
  - `max_api.py` — заготовка клиента к `platform-api.max.ru` (по мере необходимости).
  - `state.py` — перечисления FSM‑состояний для сложных диалогов бота.
  - `mapping.py` — интерфейсы для маппинга MAX user → VKMax user (может использовать БД).

## 3. Связь BOT ↔ FAST_API ↔ SEVICES

- Бот **не содержит** бизнес‑логики конвертации/работы с БД.
- Бот обращается к HTTP‑слою `FAST_API` через `SERVICES.vkmax_api.VkmaxApiClient`.
- Вся тяжёлая логика по конвертации, графам, WebParser и т.п. живёт в `BACKEND/SEVICES` и `BACKEND/CONVERT` (см. `SEVICES/INSTRUCTIONS.MD`).

Примеры связок:

- `/stats` в боте → `VkmaxApiClient.get_stats()` → `GET /stats` FastAPI → `SystemManager.stats()`.
- `/formats` в боте → `VkmaxApiClient.list_formats()`/`list_supported_conversions()` → `FormatManager` в БД.
- `/convert_file` в боте → `VkmaxApiClient.create_convert_operation()` → `POST /convert` FastAPI → сервисы конвертации (через `SEVICES` / `CONVERT`).

## 4. Запуск бота локально

1. Установить зависимости для бота (как минимум `aiomax` и `httpx`).
2. В `BACKEND/.env` (или окружении) задать:

   ```bash
   VKMAX_BOT_TOKEN="<токен_бота_MAX_с_хакатона>"
   VKMAX_FASTAPI_BASE_URL="http://localhost:8000"  # или URL развёрнутого FastAPI
   VKMAX_BOT_DEBUG=1
   VKMAX_ADMIN_TOKEN="<admin_token>"  # если /stats защищён
   ```

3. Запустить FastAPI (например, через `uvicorn BACKEND.FAST_API.run_app:app`).
4. Запустить бота:

   ```bash
   python -m BACKEND.BOT.run_bot
   ```

Бот подключится к серверам MAX, начнёт long polling и сможет вызывать HTTP‑API VKMax.

## 5. Дальнейшее развитие

- Реализовать реальные запросы к `platform-api.max.ru` в `SERVICES/max_api.py`.
- Добавить полноценные FSM‑сценарии (выбор файла, формата, подтверждение) вместо простых команд.
- Подключить MAX WebApp‑авторизацию: мини‑аппа отправляет `init_data` на `/auth/max/webapp`,
  а бот и WebApp используют общий user_id VKMax.


Documentations

Skip to content
Navigation Menu
dpnspn
aiomax

Type / to search
Code
Issues
1
Pull requests
1
Actions
Projects
Wiki
Security
Insights
Бот
github-actions[bot] edited this page last month · 32 revisions
Инициализация бота
В aiomax используется класс Bot для работы с ботом.

Для примеров посмотрите на страницу Примеры.

Bot является главным роутером. Подробнее о роутерах на странице Роутеры.

Референс
Bot(access_token: str, command_prefixes: str | List[str] = '/', mention_prefix: bool = True, case_sensitive: bool = True, default_format: Literal['markdown', 'html'] | None = None, max_messages_cached: int = 10000, debug: bool = False)
Создаёт объект класса Bot, через который можно управлять ботом.

access_token: str - токен бота, взятый с @MasterBot

command_prefixes: str | List[str] - префикс (или префиксы) команд бота. / по умолчанию

mention_prefix: bool - будет ли бот реагировать на команды, начинающиеся с его имени пользователя (формата @username /command). Без mention_prefix бот не будет работать в группах. True по умолчанию

case_sensitive: bool - важнен ли регистр при отправке команд. True по умолчанию

default_format: 'markdown' | 'html' | None - какой язык разметки использовать, если не указан в запросе. None по умолчанию

max_messages_cached: int - максимальное количество кэшированных сообщений. 10000 по умолчанию. Кэширование сообщений нужно для того, чтобы вы смогли просматривать старые версии сообщений (например, при Bot.on_message_edit). Поставьте 0, если хотите выключить кеширование.

debug: bool - Если True, все ошибки во время поллинга дают более детализированную информацию. False по умолчанию

Bot.storage: FSMStorage
FSM хранилище, присваиваемое боту. Подробнее на странице FSM

Bot.get_me() -> User
Возвращает объект класса User с информацией о профиле текущего бота.

Bot.patch_me(name: str | None, description: str | None, commands: List[BotCommand] | None, photo: ImageRequestPayload | None) -> User
Изменяет информацию о боте и принимает параметры name, description, commands, photo.

Параметры, оставленные None (по умолчанию) не будут изменены.

Возвращает объект класса User с обновленными данными.

name: str | None - новое имя бота

description: str | None - новое описание профиля бота

commands: List[BotCommand] | None - новый список команд бота

photo: ImageRequestPayload | None - новая аватарка бота в виде объекта класса ImageRequestPayload

Bot.get_chats(count: int | None = None, marker: int | None = None) -> Chat
Возвращает список объектов класса Chat с чатами в которых состоит бот.

count: int - максимальное количество чатов на одной странице

marker: int - маркер для смены страницы, который вы получили с другого вызова get_chats

Bot.chat_by_link(link: str)
Возвращает объект класса Chat чата с указанной ссылкой

link: str - ссылка на чат
Bot.get_chat(chat_id: int) -> Chat
Возвращает объект класса Chat чата с указанным ID.

chat_id: int - ID чата
Bot.get_pin(chat_id: int) -> Message | None
Возвращает объект класса Message с закрепленным сообщением, или None, если в чате нет закрепленных сообщений.

chat_id: int - ID чата, в котором нужно посмотреть закрепленное сообщение
Bot.pin(chat_id: int, message_id: str, notify: bool | None = None)
Закрепляет сообщение в чате.

chat_id: int - ID чата, в котором нужно закрепить сообщение

message_id: str - ID сообщения, которое нужно закрепить

notify: bool | None - уведомлять ли пользователей о закреплении сообщения. True по умолчанию

Bot.delete_pin(chat_id: int)
Удаляет закрепленное сообщение в чате.

chat_id: int - ID чата
Bot.my_membership(chat_id: int) -> User
Возвращает объект класса User с информацией о боте в том или ином чате.

chat_id: int - ID чата
Bot.leave_chat(chat_id: int)
Заставляет бота покинуть тот или иной чат.

chat_id: int - ID чата
Bot.get_admins(chat_id: int) -> List[User]
Возвращает список администраторов чата.

chat_id: int - ID чата
Bot.get_members(chat_id: int, count_per_iter: int = 100) -> AsyncIterator[User]
Возвращает асинхронный итератор с пользователями в чате.

chat_id: int - ID чата

count_per_iter: int - Количество пользователей, запрашиваемое у API за один запрос. Не может быть больше 100

Примеры:

# Вывод всех пользователей в чате в консоль последовательно
async for user in bot.get_members(chat_id):
    print(user.user_id, user.name)
# Выбор случайного пользователя в чате
users = [i async for i in bot.get_members(chat_id)]
print(random.choice(users).name)
Bot.get_memberships(chat_id: int, user_ids: List[int]) -> List[User] | User | None
Возвращает список пользователей из чата с указанными ID.

chat_id: int - ID чата

user_ids: List[int] - список ID пользователей

Если user_ids - список, то возвращает список найденных в чате пользователей.

Если user_ids - один элемент, то возвращает объект класса User с информацией о пользователе, либо None, если пользователя нет в чате.

Bot.add_members(chat_id: int, users: List[int])
Добавляет в чат определенных пользователей.

chat_id: int - ID чата

users: List[int] - список ID пользователей, которых нужно добавить в чат

Bot.kick_member(chat_id: int, user_id: int)
Удаляет пользователя из чата.

chat_id: int - ID чата

user_id: int - ID пользователя, которого нужно удалить из чата

block: bool | None - Надо ли блокировать пользователя? False по умолчанию

Bot.patch_chat(chat_id: int, icon: ImageRequestPayload | None = None, title: str | None = None, pin: str | None = None, notify: bool | None = None)
Изменяет информацию о чате, например имя, иконку или закрепленное сообщение (для последнего также есть Bot.pin).

Все аргументы, кроме chat_id, необязательны.

Возвращает объект класса Chat с обновленными данными о чате

chat_id: int - ID чата

icon: ImageRequestPayload | None - новая иконка чата в виде объекта класса ImageRequestPayload

title: str | None - новое название чата

pin: str | None - ID сообщения, которое нужно закрепить

notify: bool | None - отправлять ли участникам чата уведомление об изменении чата

Bot.post_action(chat_id: int, action: str)
Отправляет какое-либо действие бота в чат, например показывание иконки "печатает" или выставления галочки прочитывания сообщений.

chat_id: int - ID чата

action: str - нужное действие. Все возможные действия - typing_on, sending_photo, sending_audio, sending_file, mark_seen (также находятся в классе Actions)

Bot.upload_image(data: IO | str) -> PhotoAttachment
Загружает картинку на сервер. Возвращает PhotoAttachment.

data: IO | str - Путь к файлу или file-like объект.
Bot.upload_video(data: IO | str) -> VideoAttachment
Загружает видео на сервер. Возвращает VideoAttachment.

data: IO | str - Путь к файлу или file-like объект.
Bot.upload_audio(data: IO | str) -> AudioAttachment
Загружает аудиофайл на сервер. Возвращает AudioAttachment.

data: IO | str - Путь к файлу или file-like объект.
Bot.upload_file(data: IO | str, filename: str | None = None) -> FileAttachment
Загружает файл на сервер. Возвращает FileAttachment.

data: IO | str - Путь к файлу или file-like объект.

filename: str | None - Имя файла, отображаемое у пользователей. Обязательно при использовании io.BytesIO.

Bot.get_message(id: str) -> Message
Получает информацию о сообщении по его ID. Возвращает Message.

data: IO | str - Путь к файлу или file-like объект.
Bot.send_message(text: str | None, chat_id: int | None = None, user_id: int | None = None, format: 'markdown' | 'html' | 'default' | None = 'default', reply_to: int | None = None, notify: bool = True, disable_link_preview: bool = False, keyboard: List[List[buttons.Button]] | buttons.KeyboardBuilder | None = None, attachments: List[Attachment] | Attachment | None = None) -> Message
Отправляет сообщение в нужный чат. Возвращает Message.

text: str - текст сообщения. Максимум 4000 символов

chat_id: int - ID чата, куда отправить сообщение. Не может быть использован вместе с user_id

user_id: int - ID пользователя, кому отправить сообщение. Не может быть использован вместе с chat_id

format: 'markdown' | 'html' | 'default' | None - режим форматирования сообщения. None - без форматирования, default - режим форматирования по умолчанию (устанавливается при инициализации Bot). Необязательно

reply_to: int - ID сообщения, на которое нужно ответить. Необязательно

notify: bool - уведомлять ли пользователей о сообщении. True по умолчанию

disable_link_preview: bool - спрятать ли предпросмотр ссылок. False по умолчанию

keyboard: List[List[buttons.Button]] | buttons.KeyboardBuilder | None - клавиатура, которую надо прикрепить к сообщению.

attachments: List[Attachment] | Attachment | None - список вложений, которые нужно прикрепить к сообщению

Bot.edit_message(message_id: str, text: "str | None" = None, format: 'markdown' | 'html' | 'default' | None = 'default', notify: bool = True, keyboard: List[List[buttons.Button]] | buttons.KeyboardBuilder | None = None, attachments: List[Attachment] | Attachment | None = None) -> Message
Изменяет содержимое сообщения. Возвращает новое Message.

message_id: str - сообщение для изменения

text: "str | None" - текст сообщения. Максимум 4000 символов. Необязательно

format: 'markdown' | 'html' | 'default' | None - режим форматирования сообщения. None - без форматирования, default - режим форматирования по умолчанию (устанавливается при инициализации Bot). Необязательно

reply_to: int - ID сообщения, на которое нужно ответить. Необязательно

notify: bool - уведомлять ли пользователей о сообщении. True по умолчанию

disable_link_preview: bool - спрятать ли предпросмотр ссылок. False по умолчанию

keyboard: List[List[buttons.Button]] | buttons.KeyboardBuilder | None - новая клавиатура, которую надо прикрепить к сообщению. None не будет менять клавиатуру.

attachments: List[Attachment] | Attachment | None - новый список вложений. None не будет менять список файлов. Укажите [], чтобы удалить все вложения - это также удалит клавиатуру, если она есть.

Bot.delete_message(message_id: str)
Удаляет сообщение.

message_id: str - ID сообщения для удаления.
Bot.start_polling(session: "aiohttp.ClientSession | None" = None)
Начинает Long polling. Может использоваться обёрнутым в asyncio.run() в конце программы для запуска бота.

session: aiohttp.ClientSession | None - aiohttp сессия. Если None, создаётся сама
Bot.run()
Начинает Long polling. Является коротким синтаксисом для asyncio.run(Bot.start_polling()).

Pages 10
Find a page…
Home
FSM
Бот
Инициализация бота
Референс
Bot(access_token: str, command_prefixes: str | List[str] = '/', mention_prefix: bool = True, case_sensitive: bool = True, default_format: Literal['markdown', 'html'] | None = None, max_messages_cached: int = 10000, debug: bool = False)
Bot.storage: FSMStorage
Bot.get_me() -> User
Bot.patch_me(name: str | None, description: str | None, commands: List[BotCommand] | None, photo: ImageRequestPayload | None) -> User
Bot.get_chats(count: int | None = None, marker: int | None = None) -> Chat
Bot.chat_by_link(link: str)
Bot.get_chat(chat_id: int) -> Chat
Bot.get_pin(chat_id: int) -> Message | None
Bot.pin(chat_id: int, message_id: str, notify: bool | None = None)
Bot.delete_pin(chat_id: int)
Bot.my_membership(chat_id: int) -> User
Bot.leave_chat(chat_id: int)
Bot.get_admins(chat_id: int) -> List[User]
Bot.get_members(chat_id: int, count_per_iter: int = 100) -> AsyncIterator[User]
Bot.get_memberships(chat_id: int, user_ids: List[int]) -> List[User] | User | None
Bot.add_members(chat_id: int, users: List[int])
Bot.kick_member(chat_id: int, user_id: int)
Bot.patch_chat(chat_id: int, icon: ImageRequestPayload | None = None, title: str | None = None, pin: str | None = None, notify: bool | None = None)
Bot.post_action(chat_id: int, action: str)
Bot.upload_image(data: IO | str) -> PhotoAttachment
Bot.upload_video(data: IO | str) -> VideoAttachment
Bot.upload_audio(data: IO | str) -> AudioAttachment
Bot.upload_file(data: IO | str, filename: str | None = None) -> FileAttachment
Bot.get_message(id: str) -> Message
Bot.send_message(text: str | None, chat_id: int | None = None, user_id: int | None = None, format: 'markdown' | 'html' | 'default' | None = 'default', reply_to: int | None = None, notify: bool = True, disable_link_preview: bool = False, keyboard: List[List[buttons.Button]] | buttons.KeyboardBuilder | None = None, attachments: List[Attachment] | Attachment | None = None) -> Message
Bot.edit_message(message_id: str, text: "str | None" = None, format: 'markdown' | 'html' | 'default' | None = 'default', notify: bool = True, keyboard: List[List[buttons.Button]] | buttons.KeyboardBuilder | None = None, attachments: List[Attachment] | Attachment | None = None) -> Message
Bot.delete_message(message_id: str)
Bot.start_polling(session: "aiohttp.ClientSession | None" = None)
Bot.run()
Декораторы
Клавиатуры
Логи
Примеры
Роутеры
Типы
Фильтры
Clone this wiki locally
https://github.com/dpnspn/aiomax.wiki.git
Footer
© 2025 GitHub, Inc.
Footer navigation
Terms
Privacy
Security
Status
Community
Docs
Contact
Manage cookies
Do not share my personal information
Бот · dpnspn/aiomax Wiki

Skip to content
Navigation Menu
dpnspn
aiomax

Type / to search
Code
Issues
1
Pull requests
1
Actions
Projects
Wiki
Security
Insights
Декораторы
github-actions[bot] edited this page last month · 42 revisions
Декораторы используются для обработки поступающих запросов с Max API - например, получения сообщений или поступления команд. Они доступны для использования в роутерах.

Каждый декоратор, кроме Bot.on_button_chat_create(), также отправляет функции объект класса FSMCursor как аргумент cursor используя user_id пользователя, совершившего действие. Подробнее на странице FSM

on_message(filter: Callable | str | None = None, detect_commands: bool = False)
Декоратор для получения сообщений.

Поддерживает фильтры. Вставьте Callable функцию в параметр функции on_message - в неё при отправке сообщения будет передаваться Message. Если она вернет True, функция вызовется.

Если вставить str, то будет вызываться в случае, если текст отправленного сообщения будет равен str.

Если не вставлять фильтр, функция вызовется при любом отправленном сообщении.

Если detect_commands == True, то декоратор сработает независимо от того, является ли сообщение командой или нет.

Отправляет функции объект класса Message.

on_message_edit(filter: Callable | str | None = None)
Декоратор для получения сообщений при их редактировании.

Отправляет функции два объекта:

первый (before) - предыдущее состояние сообщения Message. None, если выключен кэш сообщений в Bot или если сообщения нет в кэше.

второй (after) - новое состояние сообщения Message.

Поддерживает фильтры. Вставьте Callable функцию в параметр функции on_message_edit - в неё при изменении сообщения будет передаваться Message (новое состояние). Если она вернет True, функция вызовется.

Если вставить str, то будет вызываться в случае, если новый текст измененного сообщения будет равен str.

Если не вставлять фильтр, функция вызовется при любом измененном сообщении.

on_message_delete(filter: Callable | str | None = None)
Декоратор для получения сообщений при их удалении.

Поддерживает фильтры. Вставьте Callable функцию в параметр функции on_message_delete - в неё при удалении сообщения будет передаваться MessageDeletePayload. Если она вернет True, функция вызовется.

Если вставить str, то будет вызываться в случае, если удаленное сообщение кешировано и текст удаленного сообщения будет равен str.

Если не вставлять фильтр, функция вызовется при любом удаленном сообщении.

Отправляет функции объект класса MessageDeletePayload.

on_bot_start()
Декоратор вызывается, когда пользователь жмет кнопку "Начать" в ЛС с ботом.

Отправляет функции объект класса BotStartPayload.

on_ready()
Декоратор вызывается перед началом долгого опроса (поллинга).

on_command(name: "str | None" = None, aliases: List[str] = [], as_message: bool = False)
Декоратор для получения команд с префиксом.

Принимает name - название команды и aliases - список с альтернативными названиями команд.

Если переданный as_message является False, то сообщение с командой не будет отправляться обработчикам on_message, у которых detect_commands является False.

Если name не указан, то название команды берется из имени функции.

Отправляет функции объект класса CommandsContext.

on_button_callback(filter: Callable | None = None)
Декоратор для отслеживания нажатий на кнопки типа CallbackButton.

Поддерживает фильтры. Вставьте Callable функцию в параметр функции on_button_callback - в неё при отправке сообщения будет передаваться Callback. Если она вернет True, функция вызовется.

Если вставить str, то будет вызываться в случае, если Callable.payload равен str.

Отправляет функции объект класса Callback.

on_button_chat_create()
Декоратор для отслеживания нажатий на создание чатов с помощью кнопки типа ChatButton.

Отправляет функции объект класса ChatCreatePayload.

on_bot_add()
Декоратор для отслеживания добавления бота в чаты.

Отправляет функции объект класса ChatMembershipPayload.

on_bot_remove()
Декоратор для отслеживания удаления бота с чатов.

Отправляет функции объект класса ChatMembershipPayload.

on_user_add()
Декоратор для отслеживания добавления или входа пользователей в чаты.

Отправляет функции объект класса UserMembershipPayload.

on_user_remove()
Декоратор для отслеживания удаления или выхода пользователей с чатов.

Отправляет функции объект класса UserMembershipPayload.

on_chat_title_change()
Декоратор для отслеживания изменений названий чатов.

Отправляет функции объект класса ChatTitleEditPayload.

Pages 10
Find a page…
Home
FSM
Бот
Декораторы
on_message(filter: Callable | str | None = None, detect_commands: bool = False)
on_message_edit(filter: Callable | str | None = None)
on_message_delete(filter: Callable | str | None = None)
on_bot_start()
on_ready()
on_command(name: "str | None" = None, aliases: List[str] = [], as_message: bool = False)
on_button_callback(filter: Callable | None = None)
on_button_chat_create()
on_bot_add()
on_bot_remove()
on_user_add()
on_user_remove()
on_chat_title_change()
Клавиатуры
Логи
Примеры
Роутеры
Типы
Фильтры
Clone this wiki locally
https://github.com/dpnspn/aiomax.wiki.git
Footer
© 2025 GitHub, Inc.
Footer navigation
Terms
Privacy
Security
Status
Community
Docs
Contact
Manage cookies
Do not share my personal information
Декораторы · dpnspn/aiomax Wiki

Клавиатуры
github-actions[bot] edited this page last month · 23 revisions
buttons.KeyboardBuilder
Для создания клавиатуры необходимо инициализировать класс buttons.KeyboardBuilder.

Для добавления кнопок на клавиатуру можно использовать следующие функции, передав им CallbackButton, LinkButton, GeolocationButton, ContactButton или ChatButton:

Все функции (кроме to_list) возвращают клавиатуру, то есть возможен вариант написания kb = KeyboardBuilder().add(**buttons)

KeyboardBuilder.row(*buttons: List[Button])
Добавляет новый ряд кнопок с переданными кнопкой / кнопками.

KeyboardBuilder.add(*buttons: List[Button])
Добавляет кнопку / кнопки на последний ряд клавиатуры.

KeyboardBuilder.table(in_row: int, *buttons: List[Button])
Добавляет кнопки на несколько рядов так, чтобы в каждом ряду было по in_row кнопок.

KeyboardBuilder.to_list()
Конвертирует клавиатуру в сериализуемый список, который можно использовать при отправке сообщения. Функции для отправки сообщения вызывают это автоматически.

Типы кнопок
CallbackButton(text: str, payload: str, intent: Literal['default', 'positive', 'negative'] = 'default')
Кнопка, при нажатии которой боту придёт ивент message_callback, который можно поймать декоратором on_button_callback.

text: str - текст кнопки

payload: str - Payload, который передастся в message_callback

intent: Literal['default', 'positive', 'negative'] - намерение кнопки. Влияет на отображение клиентом

LinkButton(text: str, url: str)
Кнопка-ссылка, при нажатии на которую у пользователя откроется веб-страница.

text: str - текст кнопки

url: str - ссылка, на которую ведет кнопка

GeolocationButton(text: str, quick: bool = False)
Кнопка, при нажатии на которую пользователь сможет отправить геолокацию в чат.

text: str - текст кнопки

quick: bool - если False, то пользователь сможет просмотреть и выбрать геолокацию в открытом окне. Если True, то пользователю покажется только быстрое подтверждение о том, отправлять ли свою геолокацию. False по умолчанию

ContactButton(text: str)
Кнопка, при нажатии на которую пользователь сможет отправить свою контактную информацию.

text: str - текст кнопки
ChatButton(text: str, title: str, description: str | None = None, payload: str | None = None, uuid: int | None = None)
Кнопка, при нажатии на которую пользователь сможет создать новый чат. Бот будет автоматически добавлен в новый чат. Создание такого чата можно отследить декоратором on_button_chat_create.

text: str - текст кнопки

title: str - название нового чата

description: str | None - описание нового чата. None по умолчанию

payload: str | None - Payload, который будет передан функциям с декоратором Bot.on_button_chat_create при создании чата. None по умолчанию

uuid: int | None - UUID, который будет создан автоматически при отправке сообщения. Каждый отдельный UUID создаёт отдельный чат, чтобы при нажатию на одну и ту же кнопку несколько раз открывался или создавался один и тот же чат. Укажите UUID, стоявший на прошлой кнопке при редактировании сообщения - при отправке сообщения указывать UUID не надо.

WebAppButton(text: str, bot: str | int)
Кнопка, при нажатии на которую пользователю откроется веб-приложение того или иного бота.

text: str - текст кнопки

bot: str | int - ID, имя пользователя или ссылка на бота, Web-app которого нужно открыть

MessageButton(text: str)
Кнопка, при нажатии на которую пользователь отправит в чат определенный текст.

text: str - текст кнопки. При нажатии на кнопку пользователь отправит этот текст в чат
Pages 10
Find a page…
Home
FSM
Бот
Декораторы
Клавиатуры
buttons.KeyboardBuilder
KeyboardBuilder.row(*buttons: List[Button])
KeyboardBuilder.add(*buttons: List[Button])
KeyboardBuilder.table(in_row: int, *buttons: List[Button])
KeyboardBuilder.to_list()
Типы кнопок
CallbackButton(text: str, payload: str, intent: Literal['default', 'positive', 'negative'] = 'default')
LinkButton(text: str, url: str)
GeolocationButton(text: str, quick: bool = False)
ContactButton(text: str)
ChatButton(text: str, title: str, description: str | None = None, payload: str | None = None, uuid: int | None = None)
WebAppButton(text: str, bot: str | int)
MessageButton(text: str)
Логи
Примеры
Роутеры
Типы
Фильтры
Clone this wiki locally
https://github.com/dpnspn/aiomax.wiki.git
Footer
© 2025 GitHub, Inc.
Footer navigation
Terms
Privacy
Security
Status
Community
Docs
Contact


Логи
mbutsk edited this page on Jun 18 · 1 revision
Логирование нужно чтобы четчё понимать какие события происходят с ботом

Инициализация
Для начала импортируйте стандартную библиотеку logging: import logging В коде (обычно в конце main.py) должна быть строка logging.basicConfig(level=level) Подробнее о уровнях ниже

INFO
Для стандартной работы бота обычно пишут logging.basicConfig(level=logging.INFO) Значит в логах будет информация (например, о том, что бот запущен) и ошибки при поллинге

DEBUG
При дебаге бота следует писать logging.basicConfig(level=logging.DEBUG) В этом случае в логах будет то же что и в INFO, а также информация о сообщениях и коллбэках, которые были хендлены и не были

Примеры
github-actions[bot] edited this page last month · 41 revisions
Инициализация бота
Для начала нужно создать бота и получить его токен в @MasterBot.

Этот токен нужно вставить везде, где написано 'TOKEN'.

Эхо-бот
import aiomax
import asyncio

bot = aiomax.Bot('TOKEN')

@bot.on_message()
async def echo(message: aiomax.Message):
    await message.reply(message.body.text)

bot.run()
Генератор рандомных чисел
import aiomax
import asyncio
import random

bot = aiomax.Bot('TOKEN', default_format='markdown')

# Команда для генерации случайных чисел: /random минимум максимум
@bot.on_command('random', aliases=['rnd'])
async def gen(ctx: aiomax.CommandContext):
    try:
        min_num = int(ctx.args[0])
        max_num = int(ctx.args[1])
        number = random.randint(min_num, max_num)
    except:
        await ctx.reply('❌ **Некорректные аргументы!**\n\n/random <миниммум> <максимум>')
        return

    await ctx.reply(f'Ваше число: **{number}**')

# Сообщение при начале чата с ботом
@bot.on_bot_start()
async def on_bot_start(payload: aiomax.BotStartPayload):
    await payload.send('**Моя команда:**\n\n/random <минимум> <максимум>')

# Отправляет команды на сервер, чтобы они отображались у пользователей в меню
@bot.on_ready()
async def send_commands():
    await bot.patch_me(commands=[
        aiomax.BotCommand('random', 'Генерирует случайное число от минимума до максимума')
    ])

bot.run()
Эхо-бот с проверкой на чат
import aiomax
import asyncio

bot = aiomax.Bot('TOKEN')

chat_id: int = 2409 # ID чата, сообщения в котором должны обрабатыватся

@bot.on_message(lambda message: message.recipient.chat_id == chat_id)
async def echo(message: aiomax.Message):
    await message.send(message.body.text)

bot.run()
Простой счётчик со сбросом
import aiomax
import asyncio

bot = aiomax.Bot('TOKEN')
taps = 0

# Команда отправляющая сообщение с кнопками
@bot.on_command('tap')
async def tap_command(ctx: aiomax.CommandContext):
    kb = aiomax.buttons.KeyboardBuilder()
    kb.add(aiomax.buttons.CallbackButton('Тап', 'tap'))
    kb.row(aiomax.buttons.CallbackButton('Сбросить', 'reset'))

    await ctx.reply(f'Тапов: {taps}', keyboard=kb)

# Обработчик кнопки "Тап" (увеличение счетчика)
@bot.on_button_callback(lambda data: data.payload == 'tap')
async def tap(cb: aiomax.Callback):
    global taps
    taps += 1
    await cb.answer(text=f'Тапов: {taps}', format='markdown')

# Обработчик кнопки "Сбросить" (сброс счетчика)
@bot.on_button_callback(lambda data: data.payload == 'reset')
async def reset(cb: aiomax.Callback):
    global taps
    taps = 0
    await cb.answer('Вы сбросили все тапы!', text=f'Тапов: {taps}')

bot.run()
Разделение на несколько файлов через роутеры
echo.py
import aiomax

router = aiomax.Router()

@router.on_message()
async def echo(message: aiomax.Message):
    await message.reply(message.content)
main.py
import aiomax
import echo

bot = aiomax.Bot('TOKEN')
bot.add_router(echo.router)

bot.run()
Глобальные фильтры
import aiomax

bot = aiomax.Bot('TOKEN')
command_router = aiomax.Router()
command_router.add_message_filter(aiomax.filters.startswith('$'))

# эти функции сработают только если сообщение начинается с '$'

@command_router.on_message()
async def echo(message: aiomax.Message):
    await message.reply(message.content)

@command_router.on_message()
async def name(message: aiomax.Message):
    await message.reply(message.sender.name)

# эта функция сработает всегда

@bot.on_message()
async def echo(message: aiomax.Message):
    await message.reply(message.content)

bot.add_router(command_router)
bot.run()
Ввод имени и фамилии с помощью FSM
import aiomax
from aiomax import fsm

bot = aiomax.Bot('TOKEN')


# Запуск бота пользователем
@bot.on_bot_start()
async def start(pd: aiomax.BotStartPayload, cursor: fsm.FSMCursor):
    await pd.send("Как Вас зовут?")
    cursor.change_state('name')  # Изменения состояние


# Ввод имени
@bot.on_message(aiomax.filters.state('name'))
async def write_name(message: aiomax.Message, cursor: fsm.FSMCursor):
    await message.reply("Напишите свою фамилию")
    cursor.change_state('surname')  # Изменения состояние
    cursor.change_data({'name': message.content})  # Добавление имени в данные

# Ввод фамилии
@bot.on_message(aiomax.filters.state('surname'))
async def write_surname(message: aiomax.Message, cursor: fsm.FSMCursor):
    name = cursor.get_data()['name']  # Получение имени из данных
    surname = message.content

    await message.reply(f"Здравствуйте, {name} {surname}")
    cursor.clear()  # Очищение состояния и данных пользователя

bot.run()
Бот с использованием прокси
import aiomax
import aiohttp
import asyncio

bot = aiomax.Bot('TOKEN')

proxy_url = 'http://url:port'
proxy_auth = aiohttp.BasicAuth("login", "pasword") # Аутенфикация прокси

# Получение и вывод страны
@bot.on_command()
async def example(ctx: aiomax.CommandContext):
    response = await bot.session.get("http://ip-api.com/json/")
    data = await response.json()
    await ctx.send(f"Country: {data.get('country')}")


async def main():
    session = aiohttp.ClientSession(proxy=proxy_url, proxy_auth=proxy_auth)
    await bot.start_polling(session)

if __name__ == "__main__":
    asyncio.run(main())
Бот с загрузкой файлов
import aiomax

bot = aiomax.Bot('TOKEN')

@bot.on_command('send_photo')
async def send_photo(ctx: aiomax.CommandContext):
    attachment = await bot.upload_image('image.png')
    await ctx.send('Фото', attachments=attachment)

bot.run()
Отправка стикеров и получение кода стикера
import aiomax

bot = aiomax.Bot('TOKEN')

# Отправка стикера с указанным кодом (2613f6)
@bot.on_command('send_sticker')
async def sticker(ctx: aiomax.CommandContext):
    await ctx.reply(attachments=[
        aiomax.StickerAttachment('2613f6')
    ])

# Ответ кодом стикера на любой отправленный боту стикер
@bot.on_message()
async def get_code(message: aiomax.Message):
    for i in message.body.attachments:
        if i.type == 'sticker':
            await message.reply(i.code)
            return

bot.run()

Роутеры
github-actions[bot] edited this page last month · 22 revisions
Роутер - aiomax.Router - это класс, который содержит обработчики событий (декораторы) и добавляется к другим роутерам при помощи add_router().

Класс aiomax.Bot является главным роутером, который запускает все обработчики событий.

Роутеры могут быть полезны, если вы хотите разделить ваш код на несколько файлов.

Пример разделенного на файлы бота можно посмотреть на странице Примеры.

Создание
Пример работы роутера:

import aiomax

bot = aiomax.Bot('TOKEN')
router = aiomax.Router()

@router.on_message() # присваиваем роутеру обработчик
async def echo(message: aiomax.Message):
    await message.reply(message.content)

bot.add_router(router) # добавляем роутер к боту
bot.run()
Это - эквивалент кода:

import aiomax

bot = aiomax.Bot('TOKEN')

@bot.on_message()
async def echo(message: aiomax.Message):
    await message.reply(message.content)

bot.run()
Объект класса aiomax.Bot, к которому привязан роутер, можно получить через router.bot:

@router.on_command('my_name')
async def my_name(message: aiomax.Message):
    await message.reply('Мое имя - '+router.bot.name)
Роутер может иметь дочерние роутеры, например:

bot = aiomax.Bot('TOKEN')

# роутер-родитель
router = aiomax.Router()

@router.on_message()
async def echo(message: aiomax.Message):
    await message.reply(message.content)

bot.add_router(router)

# дочерний роутер
child_router = aiomax.Router()

@child_router.on_message()
async def echo_second(message: aiomax.Message):
    await message.reply(message.content)

router.add_router(child_router)
Чтобы отвязать роутер от другого роутера, используется метод remove_router(router: aiomax.Router):

bot.remove_router(router)
aiomax.Router принимает единственный аргумент case_sensitive (bool, по умолчанию True), который определяет, будет ли бот реагировать на команды, зарегистрированные через @router.on_command, с отличающимся регистром.

Фильтры
Вы можете добавить фильтр на определенный декоратор, который будет задействован по всему aiomax.Router при добавлении на определенный роутер (или по всем декораторам, зарегистрированным через aiomax.Bot при добавлении на бота)

Стоит заметить, что фильтр, привязанный к боту, не будет действовать на привязанных к нему роутеров (или фильтр, привязанный к определенному роутеру, не будет действовать на других привязанных к нему роутеров)

Также, в отличии от некоторых фильтров в декораторах, фильтры в роутерах не поддерживают передачу str.

Подробнее о фильтрах на странице Фильтры.

Функции
add_message_filter(filter: callable) - Добавляет фильтр на получение сообщений (декоратор on_message).

add_message_edit_filter(filter: callable) - Добавляет фильтр на изменение сообщений (декоратор on_message_edit).

add_message_delete_filter(filter: callable) - Добавляет фильтр на удаление сообщений (декоратор on_message_delete).

add_button_callback_filter(filter: callable) - Добавляет фильтр на нажатие кнопок (декоратор on_button_callback).

Типы
github-actions[bot] edited this page last month · 36 revisions
BotCommand
Команда бота. Нужна для обновления списка команд в боте.

name: str - название команды

description: str - описание команды

User
Пользователь Max.

user_id: int - ID пользователя

first_name: str - имя пользователя

last_name: str - фамилия пользователя

name: str - полное имя пользователя (имя + фамилия)

is_bot: bool - является ли пользователь ботом

last_activity_time: int - время последней активности пользователя

username: str | None - @username пользователя. Может быть None

description: str | None - описание пользователя. Может быть None

avatar_url: str | None - ссылка на thumbnail аватара пользователя. Может быть None

full_avatar_url: str | None - ссылка на аватар пользователя. Может быть None

commands: List[BotCommand] | None - список команд бота. Не None только если User получен через Bot.get_me()

last_access_time: int | None - время последней активности пользователя в чате. Не None только если User получен через метод, связанный с каким-либо чатом.

is_owner: bool | None - является ли пользователь владельцем чата. Не None только если User получен через метод, связанный с каким-либо чатом.

is_admin: bool | None - является ли пользователь администратором чата. Не None только если User получен через метод, связанный с каким-либо чатом.

join_time: int | None - время присоединения пользователя к чату. Не None только если User получен через метод, связанный с каким-либо чатом.

permissions: List[str] | None - список разрешений пользователя в чате. Не None только если User получен через метод, связанный с каким-либо чатом.

User.__eq__()
Сравнение двух классов User сравнивает их User.user_id.

Attachment
Вложение сообщения. Имеет несколько типов.

PhotoAttachment
Вложение фото.

При отправке вложения должно быть указано либо url, либо token.

url: str | None - ссылка на изображение

token: str | None - токен изображения, полученный при загрузке. Рекомендуется использовать его при отправке

photo_id: int | None - уникальный ID изображения.

VideoAttachment
Вложение видео.

При отправке вложения должен быть указан token.

token: str | None - токен видео, полученный при загрузке.

url: str | None - ссылка на видео

thumbnail: str | None - ссылка на thumbnail. Может быть None

width: int | None - ширина видео. Может быть None

height: int | None - высота видео. Может быть None

duration: int | None - продолжительность в секундах. Может быть None

AudioAttachment
Вложение аудио.

При отправке вложения должен быть указан token.

token: str - токен аудио, полученный при загрузке

transcription: str | None - транскрипция аудио. Может быть None

FileAttachment
Вложение файла.

При отправке вложения должен быть указан token.

token: str - токен файла, полученный при загрузке

url: str | None - ссылка на файл. Может быть None

filename: str | None - имя файла. Может быть None

size: int | None - размер файла в байтах. Может быть None

StickerAttachment
Вложение стикера.

При отправке вложения должен быть указан code.

code: str - код стикера

url: str | None - ссылка на изображение стикера. Может быть None

width: int | None - ширина стикера. Может быть None

height: int | None - высота стикера. Может быть None

ContactAttachment
Вложение контакта.

При отправке вложения должны быть указаны name, contact_id, vcf_info, vcf_phone.

name: str | None - имя контакта. Используется только при отправке

contact_id: int | None - ID пользователя в Max. Используется только при отправке

vcf_info: str | None - информация о контакте в формате vCard

vcf_phone: str | None - номер телефона контакта. Используется только при отправке

max_info: User | None - информация о пользователе в Max. Используется только при получении

ShareAttachment
Предпросмотр ссылки.

url: str - ссылка

token: str | None - токен вложения

title: str | None - заголовок предпросмотра ссылки. Может быть None

description: str | None - описание предпросмотра ссылки. Может быть None

image_url: str | None - ихображение предпросмотра ссылки. Может быть None

LocationAttachment
Вложение геолокации.

latitude: float - широта

longitude: float - долгота

InlineKeyboardAttachment
Вложение инлайн-клавиатуры.

payload: List[List[buttons.Button]] - двумерный массив кнопок в виде объектов buttons.Button
Message
Информация об отправленном сообщении.

recipient: MessageRecipient - информация о получателе

body: MessageBody - информация о содержимом сообщения

timestamp: float - время отправки

sender: User - отправитель

link: LinkedMessage | None - пересланное сообщение или сообщение, на которое ответили. Может быть None

views: int | None - количество просмотров. Может быть None

url: str | None - публичная ссылка на сообщение. Может быть None для не публичных чатов или ЛС

id: str - ID сообщения. Возвращает Message.body.message_id

user_locale: str | None - язык пользователя в формате IETF BCP 47. Доступен только в ЛС

Message.__eq__()
Сравнение двух классов Message сравнивает их Message.id.

Message.__str__()
Возвращает Message.body.text.

Message.resolve_mention(replies: bool = True, message_text: bool = True, skip_bot: bool = True) -> int
Возвращает ID пользователя, которого упомянул пользователь через ответ на сообщение или в тексте.

replies: bool - учитывать ли автора отвеченного сообщения при проверке. True по умолчанию

message_text: bool - учитывать ли упоминания в тексте при проверке. True по умолчанию

skip_bot: bool - пропускать ли упоминания бота. True по умолчанию

Message.send(text: str | None, format: Literal['html', 'markdown', 'default'] | None = 'default', notify: bool = True, disable_link_preview: bool = False, keyboard: List[List[buttons.Button]] | buttons.KeyboardBuilder | None = None, attachments: List[Attachment] | Attachment | None = None) -> Message
Отправляет сообщение в чат, в который было отправлено сообщение.

text: str - текст сообщения. Максимум 4000 символов

format: Literal['html', 'markdown', 'default'] | None - формат сообщения. Bot.default_format по умолчанию

notify: bool - уведомлять ли участников о сообщении. True по умолчанию

disable_link_preview: bool - отключить предпросмотр ссылок. False по умолчанию

keyboard: List[List[buttons.Button]] | buttons.KeyboardBuilder | None - инлайн-клавиатура

attachments: List[Attachment] | Attachment | None - список вложений, которые нужно прикрепить к сообщению

Message.reply(text: str | None, format: Literal['html', 'markdown', 'default'] | None = 'default', notify: bool = True, disable_link_preview: bool = False, keyboard: List[List[buttons.Button]] | buttons.KeyboardBuilder | None = None, attachments: List[Attachment] | Attachment | None = None) -> Message
Отвечает на это сообщение.

text: str - текст сообщения. Максимум 4000 символов

format: Literal['html', 'markdown', 'default'] | None - формат сообщения. Bot.default_format по умолчанию

notify: bool - уведомлять ли участников о сообщении. True по умолчанию

disable_link_preview: bool - отключить предпросмотр ссылок. False по умолчанию

keyboard: List[List[buttons.Button]] | buttons.KeyboardBuilder | None - инлайн-клавиатура

attachments: List[Attachment] | Attachment | None - список вложений, которые нужно прикрепить к сообщению

Message.edit(text: str | None, format: Literal['html', 'markdown', 'default'] | None = 'default', notify: bool = True, disable_link_preview: bool = False, keyboard: List[List[buttons.Button]] | buttons.KeyboardBuilder | None = None, attachments: List[Attachment] | Attachment | None = None) -> Message
Редактирует это сообщение.

text: str - текст сообщения. Максимум 4000 символов

format: Literal['html', 'markdown', 'default'] | None - формат сообщения. Bot.default_format по умолчанию

notify: bool - уведомлять ли участников о сообщении. True по умолчанию

disable_link_preview: bool - отключить предпросмотр ссылок. False по умолчанию

keyboard: List[List[buttons.Button]] | buttons.KeyboardBuilder | None - инлайн-клавиатура

attachments: List[Attachment] | Attachment | None - список вложений, которые нужно прикрепить к сообщению

Message.delete()
Удаляет это сообщение.

MessageRecipient
Информация о получателе сообщения. Может быть чатом или пользователем

chat_id: int | None - ID чата

chat_type: Literal['chat', 'dialog'] - тип получателя. chat - чат, dialog - ЛС пользователя

user_id: int | None - ID пользователя, если получатель является пользователем

MessageBody
Информация о содержимом сообщения.

message_id: str - ID сообщения

seq: int - порядковый номер сообщения в чате

text: str | None - текст сообщения. Может быть None для вложений

attachments: List[Attachment] | Attachment | None - список вложений у сообщения. Может быть None

markup: List[Markup] | None - форматирование сообщения. Может быть None

Markup
Один токен форматирования сообщения.

type: Literal['strong', 'emphasized', 'monospaced', 'link', 'strikethrough', 'underline', user_mention', 'heading', 'highlighted] - тип форматирования

strong - полужирный текст

emphasized - курсивный текст

monospaced - моноширинный текст

link - ссылка

strikethrough - зачеркнутый текст

underline - подчеркнутый текст

user_mention - упоминание пользователя

heading - заголовок

highlighted - красный текст

start: int - позиция начала токена

length: int - длина токена

user_link: str | None - @username упомянутого пользователя. None если type не user_mention

user_id: int | None - ID упомянутого пользователя. None если type не user_mention

url: str | None - URL ссылки. None если type не link

LinkedMessage
Оригинальное пересланное сообщение или сообщение, на которое ответили.

type: str - тип ссылки. forward - пересланное сообщение, reply - ответ

sender: User - отправитель оригинального сообщения

message: MessageBody - содержимое оригинального сообщения

chat_id: int | None - ID чата, в котором было оригинальное сообщение. None если type не forward

BotStartPayload
Информация, отправленная функции с декоратором Bot.on_bot_start.

Декоратор вызывается при нажатии кнопки "Начать" в ЛС бота пользователем.

chat_id: int - ID чата

user: User - информация о пользователе, который нажал кнопку "Начать"

payload: str | None - дополнительная информация. Может быть None

user_locale: str | None - язык пользователя в формате IETF BCP 47. Может быть None

BotStartPayload.send(text: str | None, format: Literal['html', 'markdown', 'default'] | None = 'default', notify: bool = True, disable_link_preview: bool = False, keyboard: List[List[buttons.Button]] | buttons.KeyboardBuilder | None = None, attachments: List[Attachment] | Attachment | None = None) -> Message)
Отправляет сообщение в тот же чат, в котором был начат бот.

text: str - текст сообщения. Максимум 4000 символов

format: Literal['html', 'markdown', 'default'] | None - формат сообщения. Bot.default_format по умолчанию

notify: bool - уведомлять ли участников о сообщении. True по умолчанию

disable_link_preview: bool - отключить предпросмотр ссылок. False по умолчанию

keyboard: List[List[buttons.Button]] | buttons.KeyboardBuilder | None - инлайн-клавиатура

attachments: List[Attachment] | Attachment | None - список вложений, которые нужно прикрепить к сообщению

CommandContext
Информация, отправленная функции с декоратором Bot.on_command.

Декоратор вызывается при вводе команды.

message: Message - сообщениие с введённой командой

sender: User - отправитель сообщения. Является message.sender

recipient: MessageRecipient - получатель сообщения. Является message.recipient

command_name: str - название команды

args: List[str] - аргументы команды

args_raw: str - сырые, неразделённые пробелами аргументы команды. Полезно, если нужно обрабатывать аргументы команды, которые содержат пробелы

CommandContext.send(text: str | None, format: Literal['html', 'markdown', 'default'] | None = 'default', notify: bool = True, disable_link_preview: bool = False, keyboard: List[List[buttons.Button]] | buttons.KeyboardBuilder | None = None, attachments: List[Attachment] | Attachment | None = None) -> Message
Отправляет сообщение в чат, в который была отправлена команда.

text: str - текст сообщения. Максимум 4000 символов

format: Literal['html', 'markdown', 'default'] | None - формат сообщения. Bot.default_format по умолчанию

notify: bool - уведомлять ли участников о сообщении. True по умолчанию

disable_link_preview: bool - отключить предпросмотр ссылок. False по умолчанию

keyboard: List[List[buttons.Button]] | buttons.KeyboardBuilder | None - инлайн-клавиатура

attachments: List[Attachment] | Attachment | None - список вложений, которые нужно прикрепить к сообщению

CommandContext.reply(text: str | None, format: Literal['html', 'markdown', 'default'] | None = 'default', notify: bool = True, disable_link_preview: bool = False, keyboard: List[List[buttons.Button]] | buttons.KeyboardBuilder | None = None, attachments: List[Attachment] | Attachment | None = None) -> Message
Отвечает на сообщение с командой.

text: str - текст сообщения. Максимум 4000 символов

format: Literal['html', 'markdown', 'default'] | None - формат сообщения. Bot.default_format по умолчанию

notify: bool - уведомлять ли участников о сообщении. True по умолчанию

disable_link_preview: bool - отключить предпросмотр ссылок. False по умолчанию

keyboard: List[List[buttons.Button]] | buttons.KeyboardBuilder | None - инлайн-клавиатура

attachments: List[Attachment] | Attachment | None - список вложений, которые нужно прикрепить к сообщению

Callback
Информация, отправленная функции с декоратором Bot.on_button_callback.

Декоратор вызывается при нажатии кнопки типа CallbackButton.

timestamp: float - время нажатия кнопки

callback_id: str - ID callback-а

user: User - пользователь, нажавший кнопку

message: Message | None - сообщение, на котором находится кнопка. Может быть None, если сообщение было удалено в момент получения обновления

payload: str | None - Payload, указанный при создании CallbackButton. Может быть None

user_locale: str | None - язык пользователя в формате IETF BCP 47. Может быть None

Callback.answer(notification: "str | None" = None, text: str | None = None, format: Literal['html', 'markdown', 'default'] | None = 'default', notify: bool = True, keyboard: List[List[buttons.Button]] | buttons.KeyboardBuilder | None = None, attachments: List[Attachment] | Attachment | None = None)
Отвечает на нажатие кнопки.

Либо notification, либо text, либо attachments должны быть заданы.

Если keyboard или attachments не заданы, то они не будут изменены.

notification: "str | None" - небольшой попап-уведомление, который увидит пользователь. Может быть None

text: str | None - новый текст сообщения, на котором была кнопка. Максимум 4000 символов. Может быть None

format: Literal['html', 'markdown', 'default'] | None - формат сообщения. Bot.default_format по умолчанию

notify: bool - уведомлять ли участников о изменении сообщения. True по умолчанию

keyboard: List[List[buttons.Button]] | buttons.KeyboardBuilder | None - новая клавиатура, которую надо прикрепить к сообщению. None не будет менять клавиатуру. Укажите [], чтобы удалить клавиатуру.

attachments: List[Attachment] | Attachment | None - новый список вложений. None не будет менять список файлов. Укажите [], чтобы удалить все вложения, не включая клавиатуру.

Callback.send(text: str | None, format: Literal['html', 'markdown', 'default'] | None = 'default', notify: bool = True, disable_link_preview: bool = False, keyboard: List[List[buttons.Button]] | buttons.KeyboardBuilder | None = None, attachments: List[Attachment] | Attachment | None = None) -> Message
Отправляет сообщение в тот же чат, в котором находится сообщение с нажатой кнопкой.

text: str - текст сообщения. Максимум 4000 символов

format: Literal['html', 'markdown', 'default'] | None - формат сообщения. Bot.default_format по умолчанию

notify: bool - уведомлять ли участников о сообщении. True по умолчанию

disable_link_preview: bool - отключить предпросмотр ссылок. False по умолчанию

keyboard: List[List[buttons.Button]] | buttons.KeyboardBuilder | None - инлайн-клавиатура

attachments: List[Attachment] | Attachment | None - список вложений, которые нужно прикрепить к сообщению

Callback.reply(text: str | None, format: Literal['html', 'markdown', 'default'] | None = 'default', notify: bool = True, disable_link_preview: bool = False, keyboard: List[List[buttons.Button]] | buttons.KeyboardBuilder | None = None, attachments: List[Attachment] | Attachment | None = None) -> Message
Отвечает на сообщение, на котором была нажата кнопка.

text: str - текст сообщения. Максимум 4000 символов

format: Literal['html', 'markdown', 'default'] | None - формат сообщения. Bot.default_format по умолчанию

notify: bool - уведомлять ли участников о сообщении. True по умолчанию

disable_link_preview: bool - отключить предпросмотр ссылок. False по умолчанию

keyboard: List[List[buttons.Button]] | buttons.KeyboardBuilder | None - инлайн-клавиатура

attachments: List[Attachment] | Attachment | None - список вложений, которые нужно прикрепить к сообщению

Image(url: str)
Изображение.

url: str - ссылка на изображение
ImageRequestPayload(url: "str | None" = None, token: "str | None" = None)
Изображение, загружаемое для аватарки или иконки чата или профиля.

Либо url, либо token должны быть заданы. Не может быть задано и url и token

url: str - ссылка на изображение

token: str - токен изображения, полученный через Bot.upload_image().payload.token или с уже загруженного изображения

Chat
Чат.

chat_id: int - ID чата

type: str - тип чата. dialog для ЛС или chat для группы

status: str - кем бот является в чате.

active - бот участник чата

removed - бот был удален из чата

left - бот покинул чат

closed - чат закрыт

suspended - бот был остановлен пользователем. Доступно только если type - dialog.

title: str | None - название чата. Может быть None для ЛС

description: str | None - описание чата. Может быть None

icon: Image | None - иконка чата. Может быть None для ЛС

last_event_time: int - время последнего события в чате

participants_count: int - количество участников в чате. Для ЛС всегда 2

is_public: bool - является ли чат публичным. Для ЛС всегда False

owner_id: int | None - ID владельца чата. Может быть None для ЛС

participants: Dict[int, int] | None - словарь с ID участников и их последней активностью в чате. Может содержать пользователей с временем последней активности 0. Но может быть None если запрашивается список чатов

link: str | None - ссылка на чат. Может быть None для ЛС

messages_count: int | None - количество сообщений в чате. None, если чат не групповой

dialog_with_user: User | None - пользователь, с которым ведется диалог. None, если чат не ЛС

chat_message_id: str | None - ID сообщения, содержащего кнопку, через которую был создан чат. Для чатов, созданных через buttons.ChatButton

pinned_message: Message | None - сообщение, которое закреплено в чате. Может быть None если закреплено ничего или если запрашивается список чатов

ChatCreatePayload
Информация, отправленная функции с декоратором Bot.on_button_chat_create.

Декоратор вызывается при создании чата по кнопке типа ChatButton

chat: Chat - созданный чат

timestamp: int - время создания чата в Unixtime

message_id: str | None - ID сообщения, содержащего кнопку, через которую был создан чат. Может быть None

start_payload: str | None - указанная в нажатой кномке информация. Может быть None

MessageDeletePayload
Информация, отправляемая функции с декоратором Bot.on_message_delete.

Декоратор вызывается при удалении сообщения.

timestamp: int - время удаления сообщения

message_id: str | None - ID удаленного сообщения

chat_id: int | None - ID чата, в котором находилось сообщение

user_id: int | None - ID пользователя, который удалил сообщение

message: Message | None - сообщение, найденое в кэше бота. Если кэширование сообщений выключено или сообщение не находится в кэше, то это будет None

ChatTitleEditPayload
Информация, отправляемая функции с декоратором Bot.on_chat_title_change.

Декоратор вызывается при изменении названия чата.

timestamp: int - время изменения названия чата

user: User - пользователь, изменивший название

chat_id: int | None - ID чата, у которого поменялось название

title: str | None - новое название чата

ChatMembershipPayload
Информация, отправляемая функции с декоратором Bot.on_bot_add или Bot.on_bot_remove.

Декораторы вызываются при приглашении бота в чат или удалении бота с чата.

timestamp: int - время добавления или удаления бота

user: User - пользователь, пригласивший или удаливший бота

chat_id: int | None - ID чата, в который пригласили или с которого удалили бота

is_channel: bool - является ли чат каналом

UserMembershipPayload
Информация, отправляемая функции с декоратором Bot.on_user_add или Bot.on_user_remove.

Декораторы вызываются при заходе в чат или выходе пользователя с чата.

timestamp: int - время захода или выхода с чата

user: User - пользователь, который зашел или вышел

chat_id: int | None - ID чата, в который зашел или с которого вышел пользователь

is_channel: bool - является ли чат каналом

initiator: int | None - ID пользователя, который добавил пользователя в чат или ID админа, который удалил пользователя с чата. None если пользователь сам совершил действие


Фильтры
Фильтры - функции, которые помогают фильтровать ивенты, полученные через некоторые декораторы.

Также фильтры можно применять ко всему роутеру сразу - больше на странице Роутеры.

Встроенные фильтры
В подмодуле aiomax.filters есть несколько встроенных фильтров.

Пример использования встроенного фильтра (в данном случае aiomax.filters.startswith):

@bot.on_message(aiomax.filters.startswith('папайя'))
async def dialog(message: aiomax.Message):
    pass # Содержимое функции
В большинстве мест вместо объекта фильтра из aiomax.filters можно использовать str (эквивалент aiomax.filters.equals):

@bot.on_message('папайя')
async def dialog(message: aiomax.Message):
    pass # Содержимое функции
...или bool, например:

DEBUG = True

@bot.on_message(DEBUG) # Будет работать, если DEBUG == True
async def dialog(message: aiomax.Message):
    pass # Содержимое функции
aiomax.filters.equals(content: str)
Фильтр проверяет, чтобы контент был равен данной строке.

Поддерживает Bot.on_message и Bot.on_button_callback.

content - строка, с которой нужно сравнить контент
aiomax.filters.has(content: str)
Фильтр проверяет, чтобы контент содержал в себе данную строку.

Поддерживает Bot.on_message и Bot.on_button_callback.

content - строка, которая должна содержаться в контенте
aiomax.filters.startswith(prefix: str)
Фильтр проверяет, чтобы контент начинался с определенного префикса.

Поддерживает Bot.on_message и Bot.on_button_callback.

prefix - строка, с которой должен начинаться контент
aiomax.filters.endswith(suffix: str)
Фильтр проверяет, чтобы контент заканчивался на определенный суффикс.

Поддерживает Bot.on_message и Bot.on_button_callback.

suffix - строка, на которую должен заканчиваться контент
aiomax.filters.regex(pattern: str)
Фильтр проверяет, чтобы контент соответствовал регулярному выражению.

Поддерживает Bot.on_message и Bot.on_button_callback.

pattern - регулярное выражение
aiomax.filters.papaya
Проверяет, является ли предпоследнее слово в сообщении "папайя".

Вызывать фильтр не нужно.

Не поддерживает операторы & и |.

Поддерживает Bot.on_message и Bot.on_button_callback.

aiomax.filters.state(state: any)
Проверяет, чтобы состояние пользователя (State) равнялось state. Подробнее на странице FMS

Написание собственных фильтров
При написании собственных фильтров у вас есть 3 варианта:

lambda-выражения
Самый короткий вариант, для небольших фильтров. Пишется чаще всего в одну строку.

Пример для проверки на то, что сообщение отправлено в ЛС боту:

@bot.on_message(lambda message: message.recipient.chat_type == 'dialog')
async def dialog(message: aiomax.Message):
    pass # Содержимое функции
Функции
Использование функций через def занимает больше места, но помогает избежать повторов кода, если один и тот же фильтр используется несколько раз.

Пример для проверки на то, что сообщение отправлено в ЛС боту:

def in_dialog(message: aiomax.Message):
    return message.recipient.chat_type == 'dialog'

@bot.on_message(in_dialog) # Обратите внимание, что вызывать функцию не нужно!
async def dialog(message: aiomax.Message):
    pass # Содержимое функции
Классы
Классы используются для более сложных фильтров, принимающих различные аргументы.

Пример фильтра, принимающего тип чата и проверяющего, что сообщение отправлено именно в чате этого типа:

class ChatTypeFilter:
    def __init__(self, chat_type):
        self.chat_type = chat_type

    def __call__(self, message: aiomax.Message):
        return message.recipient.chat_type == self.chat_type

@bot.on_message(ChatTypeFilter('dialog'))
async def dialog(message: aiomax.Message):
    pass # Содержимое функции
Использование нескольких фильтров
Вы можете указать несколько фильтров в декораторах, где они поддерживаются, передавая их через запятую.

Это позволяет комбинировать различные условия без необходимости писать сложные фильтры или лямбда-выражения вручную. По умолчанию используется логика AND: обработчик сработает только в случае, если все фильтры вернули True.

@bot.on_message(
    lambda message: message.recipient.chat_id == 2409,
    lambda message: not message.sender.is_bot
)
async def bot_check(message: aiomax.Message):
    await bot.delete_message(message.id)
Если вы хотите, чтобы обработчик срабатывал если только один любой фильтр вернет True, укажите параметр mode='or':

@bot.on_message(
    aiomax.filters.equals("привет"),
    aiomax.filters.equals("hello"),
    mode='or'
)
async def greetings(message: aiomax.Message):
    await message.reply("Добрый день! Good afternoon!")
Также во встроенных фильтрах поддерживаются операторы & и | для тех же целей.

Эквивалент примера с and выше:

@bot.on_message(
    lambda message: message.recipient.chat_id == 2409 &
    lambda message: not message.sender.is_bot
)
async def bot_check(message: aiomax.Message):
    await bot.delete_message(message.id)
Эквивалент примера or:

@bot.on_message(
    aiomax.filters.equals("привет") |
    aiomax.filters.equals("hello")
)
async def greetings(message: aiomax.Message):
    await message.reply("Добрый день! Good afternoon!")

