#!/usr/bin/env python3
"""
Примеры использования testTgAccApi
Демонстрирует работу с .session файлами, LLM и Media Forwarder
"""

import asyncio
from session_manager import SessionManager
from llm_handler import LLMHandler
from media_forwarder import MediaForwarder
from telethon import TelegramClient


# ============================================================================
# Пример 1: Базовое использование - загрузка сессии и получение информации
# ============================================================================

async def example_1_basic_session_usage():
    """
    Пример 1: Загрузить готовый .session файл и получить информацию об аккаунте
    """
    print("\n" + "=" * 70)
    print("Пример 1: Базовое использование .session файла")
    print("=" * 70)

    api_id = 123456  # Подставьте свой api_id
    api_hash = "your_api_hash"  # Подставьте свой api_hash

    try:
        # Создаём менеджер сессии
        manager = SessionManager(
            api_id=api_id,
            api_hash=api_hash,
            session_name="example_session",
            session_file_path="./sessions/my_account.session",  # Путь к готовому .session файлу
        )

        # Инициализируем клиент (если сессия валидна, авторизация будет пропущена)
        client = await manager.initialize_client()

        # Получаем информацию о пользователе
        me = await client.get_me()
        print(f"✓ Авторизован как: {me.first_name} @{me.username}")
        print(f"  ID: {me.id}")

        # Получаем количество диалогов
        dialogs = await client.get_dialogs(limit=5)
        print(f"\n✓ Последние 5 диалогов:")
        for dialog in dialogs:
            print(f"  - {dialog.title or dialog.name}")

        # Сохраняем сессию для резервной копии
        await manager.save_session("./sessions/backup.session")
        print(f"\n✓ Сессия сохранена в резервную копию")

        # Отключаемся
        await client.disconnect()

    except FileNotFoundError:
        print("⚠ Файл сессии не найден. Сначала авторизуйтесь через основной скрипт.")
    except Exception as e:
        print(f"✗ Ошибка: {e}")


# ============================================================================
# Пример 2: Использование LLM обработчика для авто-ответов
# ============================================================================

async def example_2_llm_auto_responder():
    """
    Пример 2: Использовать LLM для автоматического ответа на сообщения
    """
    print("\n" + "=" * 70)
    print("Пример 2: Автоматические ответы через LLM")
    print("=" * 70)

    api_id = 123456
    api_hash = "your_api_hash"

    try:
        # Инициализируем сессию
        manager = SessionManager(
            api_id=api_id,
            api_hash=api_hash,
            session_file_path="./sessions/my_account.session",
        )
        client = await manager.initialize_client()

        # Создаём LLM обработчик
        llm_handler = LLMHandler(
            api_url="http://127.0.0.1:5000/api/v1/chat/completions",
            system_prompt="Ты полезный ассистент в Telegram. Отвечай кратко, максимум 100 символов.",
            allowed_chat_ids=[123456789],  # Только из этого чата
            timeout=30,
        )

        # Подключаем обработчик к клиенту
        llm_handler.attach_to_client(client)

        print("✓ LLM обработчик активирован!")
        print("  Отправьте сообщение в чат 123456789 - бот ответит автоматически")
        print("\n▶ Ожидание сообщений (Ctrl+C для выхода)...")

        # Ожидаем входящих сообщений
        try:
            await client._run_until_disconnected()
        except KeyboardInterrupt:
            print("\n▌ Остановка...")

        await client.disconnect()

    except Exception as e:
        print(f"✗ Ошибка: {e}")


# ============================================================================
# Пример 3: Автоматическая пересылка медиа
# ============================================================================

async def example_3_media_forwarder():
    """
    Пример 3: Автоматическая пересылка фото и видео в архивный канал
    """
    print("\n" + "=" * 70)
    print("Пример 3: Автоматическая пересылка медиа")
    print("=" * 70)

    api_id = 123456
    api_hash = "your_api_hash"

    try:
        # Инициализируем сессию
        manager = SessionManager(
            api_id=api_id,
            api_hash=api_hash,
            session_file_path="./sessions/my_account.session",
        )
        client = await manager.initialize_client()

        # Создаём форвардер медиа
        forwarder = MediaForwarder(
            source_chat_ids=[
                123456789,       # ID личного чата или группы
                -100987654321,   # ID канала
            ],
            target_channel_id=-100555666777,  # ID целевого архивного канала
            include_captions=True,
        )

        # Подключаем форвардер
        forwarder.attach_to_client(client)

        print("✓ Media Forwarder активирован!")
        print(f"  Мониторим чаты: {forwarder.source_chat_ids}")
        print(f"  Пересылаем в канал: {forwarder.target_channel_id}")
        print("\n▶ Ожидание медиа (Ctrl+C для выхода)...")

        # Ожидаем входящих сообщений с медиа
        try:
            await client._run_until_disconnected()
        except KeyboardInterrupt:
            print("\n▌ Остановка...")

        await client.disconnect()

    except Exception as e:
        print(f"✗ Ошибка: {e}")


# ============================================================================
# Пример 4: Комбинированное использование (все функции вместе)
# ============================================================================

async def example_4_combined_usage():
    """
    Пример 4: Использовать все функции одновременно
    """
    print("\n" + "=" * 70)
    print("Пример 4: Комбинированное использование (все функции)")
    print("=" * 70)

    api_id = 123456
    api_hash = "your_api_hash"

    try:
        # Инициализируем сессию
        manager = SessionManager(
            api_id=api_id,
            api_hash=api_hash,
            session_file_path="./sessions/my_account.session",
        )
        client = await manager.initialize_client()

        # 1. Активируем LLM обработчик
        llm_handler = LLMHandler(
            api_url="http://127.0.0.1:5000/api/v1/chat/completions",
            system_prompt="Ты дружелюбный ассистент. Помогай пользователям решать задачи.",
            allowed_chat_ids=[123456789],  # Только для этого чата
        )
        llm_handler.attach_to_client(client)
        print("✓ LLM обработчик активирован")

        # 2. Активируем Media Forwarder
        forwarder = MediaForwarder(
            source_chat_ids=[987654321, -100123456789],
            target_channel_id=-100555666777,
        )
        forwarder.attach_to_client(client)
        print("✓ Media Forwarder активирован")

        print("\n▶ Обе функции работают параллельно!")
        print("  - Входящие сообщения обрабатываются LLM")
        print("  - Медиа автоматически пересылаются в архивный канал")
        print("\nОжидание (Ctrl+C для выхода)...")

        try:
            await client._run_until_disconnected()
        except KeyboardInterrupt:
            print("\n▌ Остановка...")

        await client.disconnect()

    except Exception as e:
        print(f"✗ Ошибка: {e}")


# ============================================================================
# Пример 5: Получение ID чатов/каналов
# ============================================================================

async def example_5_get_chat_ids():
    """
    Пример 5: Получить IDs чатов и каналов для использования в конфиге
    """
    print("\n" + "=" * 70)
    print("Пример 5: Получение ID чатов и каналов")
    print("=" * 70)

    api_id = 123456
    api_hash = "your_api_hash"

    try:
        manager = SessionManager(
            api_id=api_id,
            api_hash=api_hash,
            session_file_path="./sessions/my_account.session",
        )
        client = await manager.initialize_client()

        # Получаем ID пользователя
        me = await client.get_me()
        print(f"\n✓ Ваш ID: {me.id}")

        # Получаем последние диалоги
        print("\n✓ Ваши последние диалоги (их ID):")
        dialogs = await client.get_dialogs(limit=20)
        for dialog in dialogs:
            name = dialog.title or dialog.name or "(без названия)"
            entity_id = dialog.id
            # Для каналов Telegram добавляет -100 к ID
            if hasattr(dialog.entity, "broadcast"):
                display_id = -100 * abs(entity_id)
            else:
                display_id = entity_id
            print(f"  {name}: {display_id}")

        # Можете также получить ID конкретного пользователя/канала
        print("\nДля получения ID конкретного пользователя/канала:")
        print("  entity = await client.get_entity('@username')")
        print("  print(entity.id)")

        await client.disconnect()

    except Exception as e:
        print(f"✗ Ошибка: {e}")


# ============================================================================
# Главное меню
# ============================================================================

async def main():
    """Главное меню примеров"""
    print("\n" + "=" * 70)
    print("  testTgAccApi - Примеры использования")
    print("=" * 70)
    print("\nДоступные примеры:")
    print("  1. Базовое использование .session файла")
    print("  2. Автоматические ответы через LLM")
    print("  3. Автоматическая пересылка медиа")
    print("  4. Комбинированное использование (все функции)")
    print("  5. Получение ID чатов и каналов")
    print("  0. Выход")

    choice = input("\nВыберите пример (0-5): ").strip()

    if choice == "1":
        await example_1_basic_session_usage()
    elif choice == "2":
        await example_2_llm_auto_responder()
    elif choice == "3":
        await example_3_media_forwarder()
    elif choice == "4":
        await example_4_combined_usage()
    elif choice == "5":
        await example_5_get_chat_ids()
    elif choice == "0":
        print("\nДо встречи! 👋")
        return
    else:
        print("\n✗ Неверный выбор")

    # После выполнения примера
    again = input("\n\nПовторить? (y/n): ").strip().lower()
    if again == "y":
        await main()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nПрограмма прервана пользователем")
