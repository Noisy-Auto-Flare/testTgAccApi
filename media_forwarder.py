"""
Media Forwarder - автоматическая пересылка фото и видео в приватный канал.
Отслеживает сообщения в исходных чатах и пересылает медиа в целевой канал.
"""

import logging
from typing import List, Optional, Dict, Any

from telethon import TelegramClient, events
from telethon.tl.types import (
    TypeMessage,
    Photo,
    Document,
)

logger = logging.getLogger(__name__)


class MediaForwarder:
    """
    Обработчик для автоматической пересылки фото и видео.
    Перехватывает медиа из исходных чатов и пересылает в целевой канал.
    """

    def __init__(
        self,
        source_chat_ids: List[int],
        target_channel_id: int,
        include_captions: bool = True,
    ):
        """
        Инициализация MediaForwarder.

        Args:
            source_chat_ids: Список ID чатов-источников для мониторинга
            target_channel_id: ID целевого канала для пересылки
            include_captions: Сохранять ли подписи оригинальных сообщений
        """
        self.source_chat_ids = source_chat_ids
        self.target_channel_id = target_channel_id
        self.include_captions = include_captions
        self.client: Optional[TelegramClient] = None

    def attach_to_client(self, client: TelegramClient) -> None:
        """Подключить обработчик к TelegramClient."""
        self.client = client
        client.add_event_handler(self._on_message, events.NewMessage(incoming=True))
        logger.info(f"Media Forwarder подключен. Мониторим чаты: {self.source_chat_ids}")

    def _has_media(self, message: TypeMessage) -> bool:
        """Проверить, содержит ли сообщение фото или видео."""
        if not message.media:
            return False

        media = message.media
        return isinstance(media, (Photo, Document)) or self._is_video_media(
            media
        )

    @staticmethod
    def _is_video_media(media: Any) -> bool:
        """Проверить, является ли медиа видеофайлом."""
        if isinstance(media, Document):
            # Проверяем MIME-тип документа
            mime_type = getattr(media, "mime_type", "")
            return mime_type.startswith("video/")

        return False

    def _get_source_info(self, chat_id: int) -> str:
        """Получить информацию об источнике для добавления к подписи."""
        # Может быть переопределено для получения имени чата
        return f"From: {chat_id}"

    async def _forward_media(
        self,
        message: TypeMessage,
        source_chat_id: int,
    ) -> bool:
        """
        Пересослать медиа в целевой канал.

        Args:
            message: Сообщение с медиа
            source_chat_id: ID источника

        Returns:
            True если успешно, False иначе
        """
        if not self.client:
            logger.error("Client не инициализирован")
            return False

        try:
            # Готовим подпись
            caption = message.text or ""

            if self.include_captions:
                source_info = self._get_source_info(source_chat_id)

                if caption:
                    caption = f"{caption}\n\n—\n{source_info}"
                else:
                    caption = source_info

            # Пересылаем медиа в целевой канал
            await self.client.send_file(
                self.target_channel_id,
                file=message.media,
                caption=caption,
                reply_to=None,
            )

            logger.info(
                f"✓ Медиа пересланы в канал {self.target_channel_id} "
                f"(источник: {source_chat_id})"
            )
            return True

        except Exception as e:
            logger.error(
                f"Ошибка при пересылке медиа "
                f"из {source_chat_id} в {self.target_channel_id}: {e}"
            )
            return False

    async def _on_message(self, event: events.NewMessage.Event) -> None:
        """
        Обработчик входящих сообщений.

        Args:
            event: Event объект Telethon
        """
        try:
            msg = event.message

            # Проверяем, что это сообщение из мониторимого чата
            chat_id = msg.peer_id.user_id if hasattr(msg.peer_id, "user_id") else msg.chat_id

            if chat_id not in self.source_chat_ids:
                return

            # Проверяем наличие медиа
            if not self._has_media(msg):
                return

            # Пересылаем медиа
            await self._forward_media(msg, chat_id)

        except Exception as e:
            logger.error(f"Ошибка в обработчике медиа-сообщения: {e}")

    @staticmethod
    def from_config(
        config: Dict[str, Any],
        client: TelegramClient,
    ) -> Optional["MediaForwarder"]:
        """
        Создать MediaForwarder из конфигурации.

        Args:
            config: Словарь конфигурации с ключами:
                - enabled: bool
                - source_chat_ids: List[int]
                - target_channel_id: int
                - include_captions: bool
            client: TelegramClient для подключения

        Returns:
            MediaForwarder или None если выключено
        """
        if not config.get("enabled", False):
            return None

        source_ids = config.get("source_chat_ids", [])
        target_id = config.get("target_channel_id")

        if not source_ids or not target_id:
            logger.warning("Media Forwarder конфигурация неполная (source_chat_ids или target_channel_id отсутствуют)")
            return None

        forwarder = MediaForwarder(
            source_chat_ids=source_ids,
            target_channel_id=target_id,
            include_captions=config.get("include_captions", True),
        )

        forwarder.attach_to_client(client)
        return forwarder
