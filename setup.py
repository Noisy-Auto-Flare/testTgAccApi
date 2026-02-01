#!/usr/bin/env python3
"""
Вспомогательный скрипт для начальной настройки testTgAccApi
Помогает:
1. Получить/проверить API credentials
2. Авторизоваться и сохранить .session файл
3. Получить IDs чатов и каналов
"""

import asyncio
import json
import os
from pathlib import Path
from telethon import TelegramClient
from telethon.errors import ApiIdInvalidError


def create_config_from_input() -> dict:
    """Интерактивно создать конфиг файл."""
    print("\n" + "=" * 70)
    print("НАСТРОЙКА testTgAccApi")
    print("=" * 70)

    config = {"telegram": {}, "accounts": []}

    # API credentials
    print("\n▌ Шаг 1: API Credentials")
    print("  Получите на https://my.telegram.org/apps")

    while True:
        try:
            api_id = int(input("\napi_id: ").strip())
            break
        except ValueError:
            print("⚠ api_id должен быть числом")

    api_hash = input("api_hash: ").strip()
    if not api_hash:
        print("⚠ api_hash не может быть пустым")
        return None

    config["telegram"]["api_id"] = api_id
    config["telegram"]["api_hash"] = api_hash

    # Аккаунты
    print("\n▌ Шаг 2: Добавление аккаунтов")

    while True:
        account = {
            "name": input("\nИмя аккаунта (например, account1): ").strip(),
            "session_file": None,
            "phone": None,
            "llm": {"enabled": False},
            "media_forward": {"enabled": False},
        }

        if not account["name"]:
            print("⚠ Имя не может быть пустым")
            continue

        # Выбор способа авторизации
        print("\nВыберите способ авторизации:")
        print("  1. По номеру телефона (интерактивно)")
        print("  2. Загрузить готовый .session файл")

        auth_choice = input("Выбор (1-2): ").strip()

        if auth_choice == "1":
            phone = input("Номер телефона (+79001234567): ").strip()
            if phone:
                account["phone"] = phone
        elif auth_choice == "2":
            session_path = input("Путь к .session файлу (например, ./sessions/account1.session): ").strip()
            if session_path:
                account["session_file"] = session_path

        config["accounts"].append(account)

        if input("\nДобавить еще аккаунт? (y/n): ").strip().lower() != "y":
            break

    return config


async def authorize_and_save_session(api_id: int, api_hash: str) -> None:
    """Авторизоваться и сохранить .session файл."""
    print("\n" + "=" * 70)
    print("АВТОРИЗАЦИЯ И СОХРАНЕНИЕ СЕССИИ")
    print("=" * 70)

    account_name = input("\nИмя аккаунта для сохранения: ").strip()
    if not account_name:
        print("⚠ Имя не может быть пустым")
        return

    phone = input("Номер телефона (+79001234567): ").strip()
    if not phone:
        print("⚠ Телефон не может быть пустым")
        return

    try:
        client = TelegramClient(account_name, api_id, api_hash)
        await client.connect()

        if await client.is_user_authorized():
            print("✓ Аккаунт уже авторизован")
        else:
            print("Отправляем код авторизации...")
            await client.send_code_request(phone)

            code = input("Введите код из Telegram: ").strip()

            try:
                await client.sign_in(phone, code)
                print("✓ Авторизация успешна")
            except Exception as e:
                if "SessionPasswordNeededError" in str(type(e)):
                    password = input("Введите пароль 2FA: ").strip()
                    await client.sign_in(password=password)
                    print("✓ Авторизация успешна (2FA)")
                else:
                    raise

        # Сохраняем сессию
        me = await client.get_me()
        print(f"\n✓ Авторизован как: {me.first_name} @{me.username}")

        # Сохраняем в файл
        session_dir = Path("./sessions")
        session_dir.mkdir(exist_ok=True)

        session_file = session_dir / f"{account_name}.session"
        
        # Telethon автоматически сохраняет сессию
        import shutil
        source_session = f"{account_name}.session"
        if os.path.exists(source_session):
            shutil.copy(source_session, session_file)
            print(f"✓ Сессия сохранена: {session_file}")
        else:
            print(f"⚠ Файл сессии {source_session} не найден")

        await client.disconnect()

    except ApiIdInvalidError:
        print("✗ Неверные api_id или api_hash")
    except Exception as e:
        print(f"✗ Ошибка: {e}")


async def get_chat_ids(api_id: int, api_hash: str, session_name: str) -> None:
    """Получить IDs чатов и каналов из готовой сессии."""
    print("\n" + "=" * 70)
    print("ПОЛУЧЕНИЕ ID ЧАТОВ И КАНАЛОВ")
    print("=" * 70)

    try:
        client = TelegramClient(session_name, api_id, api_hash)
        await client.connect()

        if not await client.is_user_authorized():
            print("⚠ Аккаунт не авторизован")
            await client.disconnect()
            return

        # Получаем информацию о себе
        me = await client.get_me()
        print(f"\n✓ Авторизован как: {me.first_name}")
        print(f"  Ваш ID: {me.id}")

        # Получаем диалоги
        print(f"\n✓ Ваши диалоги (limit=50):")
        dialogs = await client.get_dialogs(limit=50)

        chat_ids_info = []
        for dialog in dialogs:
            name = dialog.title or dialog.name or "(без названия)"
            entity_id = dialog.id

            # Для каналов добавляем -100
            if hasattr(dialog.entity, "broadcast") and dialog.entity.broadcast:
                display_id = -100 * abs(entity_id) if entity_id > 0 else entity_id
            else:
                display_id = entity_id

            chat_type = "Канал" if hasattr(dialog.entity, "broadcast") and dialog.entity.broadcast else "Чат"
            print(f"\n  {chat_type}: {name}")
            print(f"    ID: {display_id}")

            chat_ids_info.append({
                "name": name,
                "id": display_id,
                "type": chat_type
            })

        # Сохраняем в файл
        with open("chat_ids.json", "w", encoding="utf-8") as f:
            json.dump(chat_ids_info, f, ensure_ascii=False, indent=2)
        print(f"\n✓ Информация сохранена в chat_ids.json")

        await client.disconnect()

    except Exception as e:
        print(f"✗ Ошибка: {e}")


async def test_llm_connection(api_url: str) -> None:
    """Проверить соединение с LLM API."""
    print("\n" + "=" * 70)
    print("ПРОВЕРКА СОЕДИНЕНИЯ С LLM API")
    print("=" * 70)

    try:
        import aiohttp

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            payload = {
                "messages": [
                    {"role": "system", "content": "Ты тестовый ассистент."},
                    {"role": "user", "content": "Привет!"}
                ],
                "temperature": 0.7,
                "max_tokens": 50,
            }

            print(f"\nТестируем соединение к: {api_url}")

            async with session.post(api_url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✓ Успешное соединение!")

                    if "choices" in data:
                        response_text = data["choices"][0].get("message", {}).get("content", "")
                        print(f"  Ответ от LLM: {response_text[:100]}...")
                    elif "result" in data:
                        print(f"  Результат: {data['result'][:100]}...")

                else:
                    error_text = await response.text()
                    print(f"✗ Ошибка ({response.status}): {error_text[:200]}")

    except aiohttp.ClientConnectorError:
        print(f"✗ Не удалось подключиться к {api_url}")
        print("  Убедитесь, что text-generation-webui запущен")
    except Exception as e:
        print(f"✗ Ошибка: {e}")


async def main():
    """Главное меню настройки."""
    print("\n" + "=" * 70)
    print("  testTgAccApi - Помощник настройки")
    print("=" * 70)
    print("\nДоступные действия:")
    print("  1. Создать новый конфиг (интерактивно)")
    print("  2. Авторизоваться и сохранить .session файл")
    print("  3. Получить IDs чатов и каналов")
    print("  4. Проверить соединение с LLM API")
    print("  0. Выход")

    while True:
        choice = input("\nВыберите действие (0-4): ").strip()

        if choice == "1":
            config = create_config_from_input()
            if config:
                with open("config.json", "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                print("\n✓ Конфиг сохранен в config.json")

        elif choice == "2":
            api_id_str = input("api_id: ").strip()
            api_hash = input("api_hash: ").strip()
            try:
                api_id = int(api_id_str)
                await authorize_and_save_session(api_id, api_hash)
            except ValueError:
                print("⚠ api_id должен быть числом")

        elif choice == "3":
            api_id_str = input("api_id: ").strip()
            api_hash = input("api_hash: ").strip()
            session_name = input("Имя сессии (например, account1): ").strip()
            try:
                api_id = int(api_id_str)
                await get_chat_ids(api_id, api_hash, session_name)
            except ValueError:
                print("⚠ api_id должен быть числом")

        elif choice == "4":
            api_url = input("URL LLM API (http://127.0.0.1:5000/api/v1/chat/completions): ").strip()
            if api_url:
                await test_llm_connection(api_url)

        elif choice == "0":
            print("\nДо встречи! 👋")
            break
        else:
            print("\n⚠ Неверный выбор")


if __name__ == "__main__":
    asyncio.run(main())
