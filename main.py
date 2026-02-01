#!/usr/bin/env python3
"""
Telegram Account Manager с поддержкой:
1. Загрузки .session файлов
2. Интеграции с локальными LLM (text-generation-webui)
3. Автоматической пересылки медиа в приватный канал

Этот скрипт является главной точкой входа для управления Telegram аккаунтами
с расширенным функционалом.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any

from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.errors import ApiIdInvalidError, AuthKeyUnregisteredError, FloodWaitError
from telethon.tl.types import User

from session_manager import SessionManager
from llm_handler import LLMHandler
from media_forwarder import MediaForwarder

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class TelegramAccountManager:
    """
    Менеджер для управления несколькими Telegram аккаунтами с расширенным функционалом.
    """

    def __init__(self, config_path: str = "config.json"):
        """
        Инициализация менеджера аккаунтов.

        Args:
            config_path: Путь к файлу конфигурации (по умолчанию config.json)
        """
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self.accounts: List[Dict[str, Any]] = []
        self.clients: Dict[str, TelegramClient] = {}
        self.load_config()

    def load_config(self) -> None:
        """Загрузить конфигурацию из JSON файла."""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config = json.load(f)
            self.accounts = self.config.get("accounts", [])
            logger.info(f"✓ Конфигурация загружена из {self.config_path}")
        except FileNotFoundError:
            logger.error(f"Файл конфигурации не найден: {self.config_path}")
            logger.info("Попробуйте скопировать config.example.json в config.json")
            sys.exit(1)
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON: {e}")
            sys.exit(1)

    def _get_api_credentials(self) -> tuple[int, str]:
        """
        Получить api_id и api_hash из конфига, .env или интерактивного ввода.

        Returns:
            Кортеж (api_id, api_hash)
        """
        load_dotenv()

        # Сначала пробуем из конфига
        api_id = self.config.get("telegram", {}).get("api_id")
        api_hash = self.config.get("telegram", {}).get("api_hash")

        if api_id and api_hash and api_hash != "your_api_hash_here":
            return int(api_id), api_hash

        # Затем из .env
        if os.environ.get("TELEGRAM_API_ID") and os.environ.get("TELEGRAM_API_HASH"):
            try:
                return int(os.environ["TELEGRAM_API_ID"]), os.environ["TELEGRAM_API_HASH"]
            except ValueError:
                pass

        # Интерактивный ввод
        print("\n⚠ API параметры не найдены. Введите их вручную:")
        print("(Получить их можно на https://my.telegram.org/apps)")
        try:
            api_id = int(input("api_id: ").strip())
        except ValueError:
            logger.error("api_id должен быть числом")
            sys.exit(1)

        api_hash = input("api_hash: ").strip()
        if not api_hash:
            logger.error("api_hash не может быть пустым")
            sys.exit(1)

        return api_id, api_hash

    async def initialize_account(
        self,
        account_config: Dict[str, Any],
        api_id: int,
        api_hash: str,
    ) -> Optional[TelegramClient]:
        """
        Инициализировать аккаунт и подключить расширенные модули.

        Args:
            account_config: Конфигурация аккаунта
            api_id: Telegram API ID
            api_hash: Telegram API Hash

        Returns:
            TelegramClient или None в случае ошибки
        """
        account_name = account_config.get("name", "unknown")

        try:
            # Создаём SessionManager
            session_file = account_config.get("session_file")
            phone = account_config.get("phone")

            session_manager = SessionManager(
                api_id=api_id,
                api_hash=api_hash,
                session_name=account_name,
                session_file_path=session_file,
            )

            # Инициализируем клиент
            client = await session_manager.initialize_client(phone=phone)

            # Проверяем авторизацию
            if not await client.is_user_authorized():
                logger.error(f"Аккаунт {account_name} не авторизован")
                await client.disconnect()
                return None

            # Получаем информацию о пользователе
            me: User = await client.get_me()
            logger.info(f"✓ Аккаунт {account_name} авторизован (ID: {me.id})")

            # Подключаем LLM handler если включен
            llm_config = account_config.get("llm", {})
            if llm_config.get("enabled"):
                llm_handler = LLMHandler.from_config(llm_config, client)
                if llm_handler:
                    logger.info(f"✓ LLM обработчик активирован для {account_name}")

            # Подключаем Media Forwarder если включен
            media_config = account_config.get("media_forward", {})
            if media_config.get("enabled"):
                media_forwarder = MediaForwarder.from_config(media_config, client)
                if media_forwarder:
                    logger.info(f"✓ Media Forwarder активирован для {account_name}")

            self.clients[account_name] = client
            return client

        except FileNotFoundError as e:
            logger.error(f"Ошибка для аккаунта {account_name}: {e}")
            return None
        except AuthKeyUnregisteredError:
            logger.error(
                f"Сессия аккаунта {account_name} недействительна. "
                f"Удалите файл сессии и авторизуйтесь заново."
            )
            return None
        except ApiIdInvalidError:
            logger.error("Неверные api_id или api_hash")
            return None
        except Exception as e:
            logger.error(f"Ошибка инициализации аккаунта {account_name}: {e}")
            return None

    async def run_all_accounts(self) -> None:
        """Запустить все аккаунты и ожидать входящих сообщений."""
        api_id, api_hash = self._get_api_credentials()

        # Инициализируем все аккаунты
        initialized_accounts = []

        for account_config in self.accounts:
            account_name = account_config.get("name")
            logger.info(f"\nИнициализация аккаунта: {account_name}")

            client = await self.initialize_account(account_config, api_id, api_hash)
            if client:
                initialized_accounts.append((account_name, client))
            else:
                logger.warning(f"⚠ Не удалось инициализировать {account_name}")

        if not initialized_accounts:
            logger.error("Не удалось инициализировать ни один аккаунт")
            sys.exit(1)

        logger.info(f"\n✓ Инициализировано аккаунтов: {len(initialized_accounts)}")
        logger.info("▶ Ожидание входящих сообщений (Ctrl+C для выхода)...\n")

        # Запускаем все клиенты параллельно
        try:
            await asyncio.gather(
                *[self._run_single_account(name, client)
                  for name, client in initialized_accounts]
            )
        except KeyboardInterrupt:
            logger.info("\n▌ Остановка...")
        finally:
            # Отключаемся от всех аккаунтов
            for name, client in initialized_accounts:
                await client.disconnect()
                logger.info(f"✓ {name} отключен")

    async def _run_single_account(self, account_name: str, client: TelegramClient) -> None:
        """Запустить один аккаунт и ожидать входящих сообщений."""
        try:
            await client._run_until_disconnected()
        except Exception as e:
            logger.error(f"Ошибка в аккаунте {account_name}: {e}")

    @staticmethod
    async def show_incoming_messages(client: TelegramClient, account_name: str) -> None:
        """
        Обработчик для вывода информации о входящих сообщениях.

        Args:
            client: TelegramClient
            account_name: Имя аккаунта
        """

        @client.on(events.NewMessage(incoming=True))
        async def handler(event: events.NewMessage.Event) -> None:
            try:
                msg = event.message
                sender = await event.get_sender()
                chat = await event.get_chat()

                # Время отправки
                time_str = msg.date.strftime("%d.%m.%Y %H:%M:%S")

                # Информация об отправителе
                if isinstance(sender, User):
                    sender_name = f"{sender.first_name or ''} {sender.last_name or ''}".strip()
                    sender_username = f"@{sender.username}" if sender.username else "(нет)"
                else:
                    sender_name = getattr(sender, "title", "?")
                    sender_username = f"@{getattr(sender, 'username', '')}" if getattr(sender, "username", None) else "(нет)"

                # Название чата
                chat_title = getattr(chat, "title", None) or getattr(chat, "first_name", "личный диалог")

                # Текст сообщения
                text = msg.text or "(медиа без текста)"

                print(f"\n[{account_name}] Новое сообщение ({time_str})")
                print(f"  От: {sender_name} {sender_username}")
                print(f"  Чат: {chat_title}")
                print(f"  Текст: {text[:150]}{'…' if len(text) > 150 else ''}")

            except Exception as e:
                logger.error(f"Ошибка в обработчике сообщений: {e}")


async def main() -> None:
    """Главная функция."""
    print("=" * 60)
    print("  Telegram Account Manager v2.0")
    print("  С поддержкой .session, LLM и пересылки медиа")
    print("=" * 60)

    # Пробуем загрузить конфиг
    config_path = "config.json"
    if not os.path.exists(config_path):
        logger.error(f"\n✗ Файл {config_path} не найден!")
        logger.info(
            f"Создайте файл конфигурации на основе config.example.json:\n"
            f"  cp config.example.json config.json"
        )
        sys.exit(1)

    manager = TelegramAccountManager(config_path)
    await manager.run_all_accounts()


if __name__ == "__main__":
    asyncio.run(main())
