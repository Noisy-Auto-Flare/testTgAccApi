#!/usr/bin/env python3
"""
Проверка корректности работы Telegram API аккаунта.
Подключается к Telegram, выполняет get_me(), затем показывает входящие сообщения
в реальном времени: кто отправил, текст, время, информация об отправителе.
"""

import asyncio
import os
import sys
from typing import Optional

from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.errors import (
    ApiIdInvalidError,
    AuthKeyUnregisteredError,
    FloodWaitError,
    PhoneNumberInvalidError,
    SessionPasswordNeededError,
)
from telethon.tl.types import Channel, User


# api_id и api_hash берутся из .env (TELEGRAM_API_ID, TELEGRAM_API_HASH)
# или из интерактивного ввода, если в .env не заданы


def _media_type_name(media) -> str:
    """Краткое название типа вложения по объекту media."""
    if not media:
        return ""
    name = type(media).__name__
    if "Photo" in name:
        return "Фото"
    if "Document" in name:
        return "Документ"
    if "Video" in name:
        return "Видео"
    if "Audio" in name or "Voice" in name:
        return "Аудио"
    if "Contact" in name:
        return "Контакт"
    if "Sticker" in name:
        return "Стикер"
    if "Poll" in name:
        return "Опрос"
    return "Медиа"


async def _on_new_message(event: events.NewMessage.Event) -> None:
    """
    Обработчик входящих сообщений: выводит отправителя, текст, время и чат.
    """
    try:
        msg = event.message
        sender = await event.get_sender()
        chat = await event.get_chat()

        # Время отправки (в UTC)
        time_str = msg.date.strftime("%d.%m.%Y %H:%M:%S")

        # Информация об отправителе
        if isinstance(sender, User):
            sender_id = sender.id
            sender_username = f"@{sender.username}" if sender.username else "(без username)"
            sender_name = f"{sender.first_name or ''} {sender.last_name or ''}".strip() or "(без имени)"
        elif isinstance(sender, Channel):
            sender_id = sender.id
            sender_username = f"@{sender.username}" if getattr(sender, "username", None) else ""
            sender_name = getattr(sender, "title", "") or "(канал/группа)"
        else:
            sender_id = getattr(sender, "id", "?")
            sender_username = getattr(sender, "username", "") or ""
            sender_name = str(sender) if sender else "?"

        # Текст и вложения
        text = msg.text or "(без текста)"
        media_str = _media_type_name(msg.media)
        if media_str:
            text = f"{text} [+ {media_str}]" if text != "(без текста)" else f"[{media_str}]"

        # Название чата (личка, группа, канал)
        chat_title = getattr(chat, "title", None) or (getattr(chat, "first_name", "") or "")
        if not chat_title and hasattr(chat, "username") and chat.username:
            chat_title = f"@{chat.username}"
        chat_title = chat_title or "(личный диалог)"

        print("\n" + "─" * 50)
        print("  ВХОДЯЩЕЕ СООБЩЕНИЕ")
        print("─" * 50)
        print(f"  Время:     {time_str}")
        print(f"  От (ID):   {sender_id}")
        print(f"  Username:  {sender_username}")
        print(f"  Имя:       {sender_name}")
        print(f"  Чат:       {chat_title}")
        print(f"  Сообщение: {text[:200]}{'…' if len(text) > 200 else ''}")
        print("─" * 50 + "\n")

    except Exception as e:
        print(f"[Ошибка в обработчике сообщения: {e}]")


async def check_telegram_account(api_id: int, api_hash: str) -> None:
    """
    Подключается к Telegram, выполняет get_me() и выводит результат.
    Обрабатывает исключения и корректно закрывает соединение.
    """
    # Имя файла сессии — можно оставить для повторных запусков без ввода кода
    client = TelegramClient("check_session", api_id, api_hash)

    try:
        await client.connect()

        if not await client.is_user_authorized():
            # Аккаунт не авторизован — нужен вход по номеру телефона
            print("Ошибка: аккаунт не авторизован.")
            print("Сначала выполните авторизацию: введите номер телефона и код из Telegram.")
            phone = input("Номер телефона (с кодом страны, например +79001234567): ").strip()
            await client.send_code_request(phone)
            code = input("Код из Telegram: ").strip()
            try:
                await client.sign_in(phone, code)
            except SessionPasswordNeededError:
                password = input("Двухэтапная аутентификация (пароль): ").strip()
                await client.sign_in(password=password)

        # Тестовый запрос: информация о текущем пользователе
        me: User = await client.get_me()

        # Вывод успешного результата
        print("\n--- Подключение успешно ---")
        print(f"ID:       {me.id}")
        print(f"Username: @{me.username}" if me.username else "Username: (не задан)")
        print(f"Имя:      {me.first_name or ''} {me.last_name or ''}".strip())
        print("Телефон:  (используется для входа, в API не отображается)")

        # Подписка на входящие и ожидание сообщений
        client.add_event_handler(_on_new_message, events.NewMessage(incoming=True))
        print("\n--- Ожидание входящих сообщений (Ctrl+C для выхода) ---\n")

        try:
            await client._run_until_disconnected()
        except KeyboardInterrupt:
            pass

    except ApiIdInvalidError:
        print("Ошибка: неверные api_id или api_hash. Проверьте данные на my.telegram.org")
    except AuthKeyUnregisteredError:
        print("Ошибка: сессия недействительна. Удалите файл check_session.session и войдите заново.")
    except FloodWaitError as e:
        print(f"Ошибка: Telegram временно ограничил запросы. Подождите {e.seconds} сек. и попробуйте снова.")
    except PhoneNumberInvalidError:
        print("Ошибка: неверный номер телефона. Используйте формат +79001234567.")
    except (ConnectionError, OSError) as e:
        print(f"Ошибка сети: {e}")
        print("Проверьте интернет-соединение и доступность Telegram.")
    except Exception as e:
        print(f"Ошибка: {type(e).__name__}: {e}")

    finally:
        # Корректное закрытие соединения
        await client.disconnect()


def main() -> None:
    """Точка входа: api_id и api_hash из .env или интерактивного ввода."""
    load_dotenv()

    api_id_val: Optional[int] = None
    api_hash_val: Optional[str] = None

    # Сначала — из .env или переменных окружения
    if os.environ.get("TELEGRAM_API_ID") and os.environ.get("TELEGRAM_API_HASH"):
        try:
            api_id_val = int(os.environ["TELEGRAM_API_ID"])
            api_hash_val = os.environ["TELEGRAM_API_HASH"]
        except ValueError:
            print("Ошибка: TELEGRAM_API_ID должен быть числом.")
            sys.exit(1)

    # Иначе — интерактивный ввод
    if api_id_val is None or api_hash_val is None:
        print("Проверка Telegram API аккаунта (Telethon)\n")
        try:
            api_id_val = int(input("api_id: ").strip())
        except ValueError:
            print("Ошибка: api_id должен быть числом.")
            sys.exit(1)
        api_hash_val = input("api_hash: ").strip()

    if not api_hash_val:
        print("Ошибка: api_hash не может быть пустым.")
        sys.exit(1)

    asyncio.run(check_telegram_account(api_id_val, api_hash_val))


if __name__ == "__main__":
    main()
