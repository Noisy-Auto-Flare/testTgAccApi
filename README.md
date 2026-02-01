# Telegram Account Manager v2.0

Расширенный Python API для управления Telegram аккаунтами с поддержкой:

- 🔑 **Загрузка готовых .session файлов** (Telethon/Pyrogram)
- 🤖 **Интеграция с локальными LLM** (text-generation-webui) для авто-ответов
- 📹 **Автоматическая пересылка фото/видео** в приватный канал

## � НОВОЕ! Практические гайды

- 🎯 **[CONFIG_USAGE_GUIDE.md](CONFIG_USAGE_GUIDE.md)** - Как использовать config.json (5 примеров + пошаговое руководство)
- 📖 **[CONFIG_GUIDE.md](CONFIG_GUIDE.md)** - Полный справочник по конфигурации (10+ сценариев)
- 🔐 **[AUTHENTICATION_GUIDE.md](AUTHENTICATION_GUIDE.md)** - Гайд по авторизации и решение ошибок (RPCError 406)
- ⚡ **[QUICKSTART.md](QUICKSTART.md)** - Быстрый старт за 5 минут
- 📋 **[INSTALLATION.md](INSTALLATION.md)** - Подробная инструкция по установке

**Новичок? Начните с [CONFIG_USAGE_GUIDE.md](CONFIG_USAGE_GUIDE.md)!**
**Проблемы с авторизацией? [AUTHENTICATION_GUIDE.md](AUTHENTICATION_GUIDE.md)**

## �📋 Требования

- Python 3.8+
- [Telethon](https://docs.telethon.dev/) >= 1.36.0
- aiohttp >= 3.8.0
- python-dotenv >= 1.0.0

## 🚀 Быстрый старт

### 1. Установка

```bash
# Клонируем репо
git clone https://github.com/Noisy-Auto-Flare/testTgAccApi.git
cd testTgAccApi

# Устанавливаем зависимости
pip install -r requirements.txt
```

### 2. Получение api_id и api_hash

1. Зайдите на [my.telegram.org](https://my.telegram.org)
2. Войдите по номеру телефона
3. Перейдите в "API development tools"
4. Создайте приложение и скопируйте **api_id** и **api_hash**

### 3. Конфигурация

```bash
# Копируем пример конфига
cp config.example.json config.json

# Редактируем config.json (добавляем api_id, api_hash, конфигурируем функции)
nano config.json
```

### 4. Запуск

```bash
# Основной скрипт с расширенным функционалом
python main.py

# Или классический скрипт проверки (для совместимости)
python check_telegram_account.py
```

---

## 🔑 Функция 1: Поддержка .session файлов

### Описание

Загружайте готовые `.session` файлы вместо каждый раз вводить api_id, api_hash и номер телефона.

### Как использовать

#### Способ 1: Экспорт сессии из Telethon

```python
from telethon import TelegramClient

# Авторизуйтесь один раз, сессия сохранится в файл
client = TelegramClient("my_account", api_id, api_hash)
await client.start(phone="+79001234567")

# Файл my_account.session создан и готов к переносу
```

#### Способ 2: Конфигурация в config.json

```json
{
  "accounts": [
    {
      "name": "account1",
      "session_file": "./sessions/account1.session",
      "phone": null,
      "llm": { "enabled": false },
      "media_forward": { "enabled": false }
    }
  ]
}
```

### Возможности SessionManager

```python
from session_manager import SessionManager

# Инициализация с готовым .session файлом
manager = SessionManager(
    api_id=123456,
    api_hash="abc123def456",
    session_file_path="./account.session"
)

# Подключение и авторизация (пропустит ввод кода, если сессия валидна)
client = await manager.initialize_client()

# Сохранение текущей сессии
await manager.save_session("./backup.session")
```

---

## 🤖 Функция 2: Интеграция с локальными LLM

### Описание

Автоматически отвечайте на входящие сообщения, используя локальную языковую модель (например, text-generation-webui).

Основные возможности:
- ✅ Отправка "печатает..." во время генерации ответа
- ✅ Фильтрация по ID чатов
- ✅ Конфигурируемый системный промт
- ✅ Обработка ошибок и таймауты
- ✅ Совместимость с OpenAI-подобными API

### Установка и настройка text-generation-webui

```bash
# Клонируем репо
git clone https://github.com/oobabooga/text-generation-webui.git
cd text-generation-webui

# Устанавливаем зависимости и запускаем
bash start_linux.sh

# Запустится на http://127.0.0.1:5000
# Убедитесь, что в Settings -> API включены OpenAI-подобные endpoints
```

### Конфигурация в config.json

```json
{
  "accounts": [
    {
      "name": "account1",
      "llm": {
        "enabled": true,
        "api_url": "http://127.0.0.1:5000/api/v1/chat/completions",
        "api_key": null,
        "system_prompt": "Ты полезный ассистент в Telegram. Отвечай кратко и дружелюбно.",
        "allowed_chat_ids": [123456789, 987654321],
        "timeout": 60
      }
    }
  ]
}
```

### Параметры конфигурации

| Параметр | Тип | Описание |
|----------|-----|---------|
| `enabled` | bool | Включить/выключить LLM обработчик |
| `api_url` | str | URL API (OpenAI-совместимый формат) |
| `api_key` | str \| null | API ключ (если требуется) |
| `system_prompt` | str | Системный промт для модели |
| `allowed_chat_ids` | int[] | IDs чатов для обработки (пусто = все) |
| `timeout` | int | Таймаут запроса в секундах |

### Пример кода

```python
from llm_handler import LLMHandler
from telethon import TelegramClient

# Создание обработчика
handler = LLMHandler(
    api_url="http://127.0.0.1:5000/api/v1/chat/completions",
    system_prompt="Ты помощник. Помогай пользователям.",
    allowed_chat_ids=[123456789],  # Только эти чаты
)

# Подключение к клиенту
handler.attach_to_client(client)

# Теперь все входящие сообщения из чата 123456789
# будут автоматически перенаправлены в LLM и ответ отправлен обратно
```

### Поддерживаемые API

- ✅ **text-generation-webui** (по умолчанию)
- ✅ **OpenAI-совместимые API** (LM Studio, Ollama с OpenAI plugin и т.д.)
- ✅ **Custom API** (если поддерживают OpenAI format)

---

## 📹 Функция 3: Пересылка медиа в приватный канал

### Описание

Автоматически перехватывайте и пересылайте фото и видео из выбранных чатов в приватный канал для архивирования или обработки.

### Конфигурация в config.json

```json
{
  "accounts": [
    {
      "name": "account1",
      "media_forward": {
        "enabled": true,
        "source_chat_ids": [123456789, -100987654321],
        "target_channel_id": -100555666777,
        "include_captions": true
      }
    }
  ]
}
```

### Параметры

| Параметр | Тип | Описание |
|----------|-----|---------|
| `enabled` | bool | Включить/выключить пересылку |
| `source_chat_ids` | int[] | IDs исходных чатов/групп/каналов |
| `target_channel_id` | int | ID целевого приватного канала |
| `include_captions` | bool | Сохранять ли подписи с информацией об источнике |

### Поддерживаемые типы медиа

- 📷 Фото (включая альбомы)
- 🎥 Видео (видеосообщения, видеофайлы)
- 📄 Документы (опционально, в зависимости от типа)

### Как узнать ID чата/канала

```python
# Аккаунты/группы (положительные числа):
# @username -> https://t.me/username
# ID в Telegram Desktop: Settings -> Advanced -> Show IDs

# Каналы (отрицательные числа, начинаются с -100):
# @channel -> https://t.me/channel
# ID: -100123456789

# Пример получения ID через код:
from telethon import TelegramClient
client = TelegramClient("session", api_id, api_hash)
await client.start()

# Получить ID текущего пользователя
me = await client.get_me()
print(f"Ваш ID: {me.id}")

# Получить ID любого чата (через get_entity)
entity = await client.get_entity("@channel_username")
print(f"ID: {entity.id}")
```

### Пример кода

```python
from media_forwarder import MediaForwarder
from telethon import TelegramClient

# Создание форвардера
forwarder = MediaForwarder(
    source_chat_ids=[123456789, -100987654321],
    target_channel_id=-100555666777,
    include_captions=True
)

# Подключение к клиенту
forwarder.attach_to_client(client)

# Теперь все фото и видео из исходных чатов
# будут автоматически пересланы в целевой канал
```

---

## ⚙️ Полная конфигурация (config.json)

```json
{
  "telegram": {
    "api_id": 123456,
    "api_hash": "your_api_hash_here"
  },
  "accounts": [
    {
      "name": "main_account",
      "session_file": null,
      "phone": "+79001234567",
      "llm": {
        "enabled": false,
        "api_url": "http://127.0.0.1:5000/api/v1/chat/completions",
        "api_key": null,
        "system_prompt": "Ты полезный ассистент в Telegram.",
        "allowed_chat_ids": [],
        "timeout": 60
      },
      "media_forward": {
        "enabled": false,
        "source_chat_ids": [],
        "target_channel_id": null,
        "include_captions": true
      }
    },
    {
      "name": "backup_account",
      "session_file": "./sessions/backup.session",
      "phone": null,
      "llm": {
        "enabled": true,
        "api_url": "http://127.0.0.1:5000/api/v1/chat/completions",
        "system_prompt": "Ты профессиональный ассистент.",
        "allowed_chat_ids": [123456],
        "timeout": 60
      },
      "media_forward": {
        "enabled": true,
        "source_chat_ids": [-100123456789],
        "target_channel_id": -100987654321,
        "include_captions": true
      }
    }
  ],
  "logging": {
    "level": "INFO"
  }
}
```

---

## 📂 Структура проекта

```
testTgAccApi/
├── main.py                     # Главный скрипт (новый)
├── check_telegram_account.py   # Классический скрипт (совместимость)
├── session_manager.py          # Менеджер сессий
├── llm_handler.py              # Обработчик LLM
├── media_forwarder.py          # Форвардер медиа
├── config.example.json         # Пример конфигурации
├── config.json                 # Ваша конфигурация (в .gitignore)
├── requirements.txt            # Зависимости
└── README.md                   # Этот файл
```

---

## 🔧 Использование в коде

### Пример 1: Использование только .session файла

```python
import asyncio
from session_manager import SessionManager

async def main():
    manager = SessionManager(
        api_id=123456,
        api_hash="abc123",
        session_file_path="./account.session"
    )
    
    client = await manager.initialize_client()
    me = await client.get_me()
    print(f"Авторизован как: {me.first_name}")
    
    await client.disconnect()

asyncio.run(main())
```

### Пример 2: Использование LLM обработчика

```python
import asyncio
from session_manager import SessionManager
from llm_handler import LLMHandler

async def main():
    # Инициализируем сессию
    manager = SessionManager(api_id, api_hash, session_file_path="./account.session")
    client = await manager.initialize_client()
    
    # Подключаем LLM обработчик
    handler = LLMHandler(
        api_url="http://127.0.0.1:5000/api/v1/chat/completions",
        system_prompt="Ты помощник.",
        allowed_chat_ids=[123456789]
    )
    handler.attach_to_client(client)
    
    # Ожидаем входящих сообщений
    await client._run_until_disconnected()

asyncio.run(main())
```

### Пример 3: Использование Media Forwarder

```python
import asyncio
from session_manager import SessionManager
from media_forwarder import MediaForwarder

async def main():
    manager = SessionManager(api_id, api_hash, session_file_path="./account.session")
    client = await manager.initialize_client()
    
    # Подключаем форвардер медиа
    forwarder = MediaForwarder(
        source_chat_ids=[123456789, -100987654321],
        target_channel_id=-100555666777
    )
    forwarder.attach_to_client(client)
    
    await client._run_until_disconnected()

asyncio.run(main())
```

---

## ⚠️ Важно

- 🔒 **Файлы `.session` содержат авторизационные данные** — не коммитьте их в репозиторий
- 🔐 **config.json должен быть в `.gitignore`** — он содержит личные данные
- 📝 Используйте **config.example.json** как шаблон для конфигурации
- 🚫 **Не делитесь никогда своими api_id, api_hash, session файлами или номерами телефонов**

---

## 🐛 Основные ошибки и решения

| Ошибка | Решение |
|--------|---------|
| `FileNotFoundError: Файл сессии не найден` | Проверьте путь к session_file в config.json |
| `AuthKeyUnregisteredError` | Сессия устарела, удалите .session файл и авторизуйтесь заново |
| `LLM API не отвечает` | Проверьте, что text-generation-webui запущен на указанном адресе |
| `Таймаут при запросе к LLM` | Увеличьте `timeout` в конфиге или проверьте производительность сервера |
| `Media не пересылается` | Проверьте, что target_channel_id правильный и у аккаунта есть права на отправку |

---

## 📚 Дополнительные ресурсы

- [Telethon документация](https://docs.telethon.dev/)
- [text-generation-webui GitHub](https://github.com/oobabooga/text-generation-webui)
- [Получение Telegram API credentials](https://core.telegram.org/api/obtaining_api_id)
- [Типы ID в Telegram](https://core.telegram.org/api/peers)

---

## 📄 Лицензия

MIT License - используйте свободно!

---

## 💬 Поддержка

При возникновении проблем:
1. Проверьте логи (logging.INFO)
2. Убедитесь, что все параметры конфигурации корректны
3. Используйте интерактивный режим для тестирования отдельных функций

Удачи! 🚀
