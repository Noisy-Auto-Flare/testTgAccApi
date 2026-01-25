#!/usr/bin/env python3
"""
Проверка корректности работы Telegram API аккаунта.
Использует библиотеку Telethon для подключения и тестового запроса get_me().
"""

import asyncio
import os
import sys
from typing import Optional

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import (
    ApiIdInvalidError,
    AuthKeyUnregisteredError,
    FloodWaitError,
    PhoneNumberInvalidError,
    SessionPasswordNeededError,
)
from telethon.tl.types import User


# api_id и api_hash берутся из .env (TELEGRAM_API_ID, TELEGRAM_API_HASH)
# или из интерактивного ввода, если в .env не заданы


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
        # Номер телефона в get_me() не возвращается; пишем, что авторизация по тел. есть
        print("Телефон:  (используется для входа, в API не отображается)")

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
