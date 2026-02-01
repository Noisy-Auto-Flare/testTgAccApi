"""
Session Manager - управление сессиями Telegram аккаунтов.
Поддерживает как классические сессии, так и загрузку готовых .session файлов.
"""

import os
from pathlib import Path
from typing import Optional

from telethon import TelegramClient
from telethon.errors import (
    SessionPasswordNeededError,
    ApiIdInvalidError,
    AuthKeyUnregisteredError,
)


class SessionManager:
    """
    Менеджер для управления Telegram сессиями.
    Поддерживает инициализацию через:
    1. Существующий .session файл
    2. Традиционный способ (api_id, api_hash, phone)
    """

    def __init__(
        self,
        api_id: int,
        api_hash: str,
        session_name: str = "account",
        session_file_path: Optional[str] = None,
    ):
        """
        Инициализация SessionManager.

        Args:
            api_id: Telegram API ID
            api_hash: Telegram API Hash
            session_name: Имя сессии (без расширения .session)
            session_file_path: Путь к готовому .session файлу для загрузки
        """
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_name = session_name
        self.session_file_path = session_file_path
        self.client: Optional[TelegramClient] = None

    async def initialize_client(self, phone: Optional[str] = None) -> TelegramClient:
        """
        Инициализация и авторизация TelegramClient.

        Args:
            phone: Номер телефона (требуется, если session_file_path не задан)

        Returns:
            Авторизованный TelegramClient

        Raises:
            ValueError: Если недостаточно параметров для авторизации
            FileNotFoundError: Если session_file не существует
        """
        # Если задан путь к готовой сессии, загружаем её
        if self.session_file_path:
            return await self._load_from_session_file()

        # Иначе используем классический способ (phone + код)
        if not phone:
            raise ValueError(
                "Если session_file_path не задан, необходим номер телефона"
            )

        return await self._authorize_with_phone(phone)

    async def _load_from_session_file(self) -> TelegramClient:
        """
        Загрузка сессии из готового .session файла.

        Returns:
            Авторизованный TelegramClient

        Raises:
            FileNotFoundError: Если файл не существует
            AuthKeyUnregisteredError: Если сессия недействительна
        """
        session_path = Path(self.session_file_path)

        if not session_path.exists():
            raise FileNotFoundError(
                f"Файл сессии не найден: {self.session_file_path}"
            )

        # Извлекаем имя сессии без расширения
        session_name = session_path.stem

        # Создаём клиент, указывая путь к существующей сессии
        self.client = TelegramClient(
            str(session_path.parent / session_name),
            self.api_id,
            self.api_hash,
            device_model='Desktop',
            system_version='Linux',
            app_version='1.0'
        )

        try:
            await self.client.connect()

            # Проверяем авторизацию
            if not await self.client.is_user_authorized():
                raise AuthKeyUnregisteredError(
                    "Сессия загруженного файла недействительна или истекла"
                )

            print(f"✓ Сессия загружена из: {self.session_file_path}")
            return self.client

        except Exception as e:
            await self.client.disconnect()
            raise

    async def _authorize_with_phone(self, phone: str) -> TelegramClient:
        """
        Авторизация по номеру телефона с кодом подтверждения.

        Args:
            phone: Номер телефона в формате +79001234567

        Returns:
            Авторизованный TelegramClient

        Raises:
            AuthKeyUnregisteredError: Если авторизация не удалась
        """
        self.client = TelegramClient(
            self.session_name,
            self.api_id,
            self.api_hash,
            device_model='Desktop',
            system_version='Linux',
            app_version='1.0'
        )

        try:
            await self.client.connect()

            if await self.client.is_user_authorized():
                print(f"✓ Аккаунт уже авторизован из сохранённой сессии")
                return self.client

            # Отправляем запрос кода
            print(f"Отправляем код авторизации на номер {phone}...")
            await self.client.send_code_request(phone)

            code = input("Введите код из Telegram: ").strip()

            try:
                await self.client.sign_in(phone, code)
                print(f"✓ Авторизация успешна")
                return self.client

            except SessionPasswordNeededError:
                # Двухфакторная аутентификация
                password = input("Введите пароль 2FA: ").strip()
                await self.client.sign_in(password=password)
                print(f"✓ Авторизация успешна (2FA)")
                return self.client

        except Exception as e:
            if self.client:
                await self.client.disconnect()
            raise

    async def save_session(self, output_path: str) -> None:
        """
        Сохранить текущую сессию в файл .session.

        Args:
            output_path: Путь для сохранения (например, /path/to/account.session)
        """
        if not self.client:
            raise ValueError("Клиент не инициализирован")

        # Telethon автоматически сохраняет сессию в определённом формате
        # Здесь мы копируем уже сохранённый файл
        session_file_name = f"{self.session_name}.session"

        if os.path.exists(session_file_name):
            import shutil

            shutil.copy(session_file_name, output_path)
            print(f"✓ Сессия сохранена в: {output_path}")
        else:
            print(
                f"⚠ Файл сессии {session_file_name} не найден. "
                f"Telethon автоматически сохраняет её при авторизации."
            )

    async def get_client(self) -> TelegramClient:
        """Получить инициализированный клиент."""
        if not self.client:
            raise ValueError("Клиент не инициализирован. Вызовите initialize_client()")
        return self.client

    async def disconnect(self) -> None:
        """Безопасное отключение от Telegram."""
        if self.client:
            await self.client.disconnect()
            self.client = None
