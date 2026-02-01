"""
LLM Handler - интеграция с локальными языковыми моделями (text-generation-webui).
Обрабатывает входящие сообщения и генерирует ответы через LLM API.
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any

import aiohttp
from telethon import TelegramClient, events
from telethon.tl.types import TypeUpdate

logger = logging.getLogger(__name__)


class LLMHandler:
    """
    Обработчик для интеграции с локальной LLM (например, text-generation-webui).
    Перехватывает входящие сообщения и отправляет ответы от LLM.
    """

    def __init__(
        self,
        api_url: str,
        system_prompt: str,
        allowed_chat_ids: Optional[List[int]] = None,
        api_key: Optional[str] = None,
        timeout: int = 60,
    ):
        """
        Инициализация LLMHandler.

        Args:
            api_url: URL API LLM (например, http://127.0.0.1:5000/api/v1/chat/completions)
            system_prompt: Системный промт для LLM (роль бота)
            allowed_chat_ids: Список ID чатов для обработки (пусто = все чаты)
            api_key: API ключ для LLM (если требуется)
            timeout: Таймаут запроса к LLM в секундах
        """
        self.api_url = api_url
        self.system_prompt = system_prompt
        self.allowed_chat_ids = allowed_chat_ids or []
        self.api_key = api_key
        self.timeout = timeout
        self.client: Optional[TelegramClient] = None
        self.error_message = "Извините, сервис временно недоступен. Попробуйте позже."

    def attach_to_client(self, client: TelegramClient) -> None:
        """Подключить обработчик к TelegramClient."""
        self.client = client
        client.add_event_handler(self._on_message, events.NewMessage(incoming=True))
        logger.info("LLM обработчик подключен")

    def _should_process_chat(self, chat_id: int) -> bool:
        """Проверить, должен ли обрабатываться этот чат."""
        if not self.allowed_chat_ids:
            # Пустой список = обрабатываем все чаты
            return True
        return chat_id in self.allowed_chat_ids

    async def _send_typing_action(self, chat_id: int, duration: int = 3) -> None:
        """
        Отправить действие "печатает..." в чат.

        Args:
            chat_id: ID чата
            duration: Длительность в секундах
        """
        if not self.client:
            return

        try:
            # Отправляем typing action
            from telethon.tl.functions.messages import SetTypingRequest
            from telethon.tl.types import SendMessageTypingAction

            await self.client(
                SetTypingRequest(peer=chat_id, action=SendMessageTypingAction())
            )
        except Exception as e:
            logger.warning(f"Не удалось отправить typing action: {e}")

    async def _query_llm(self, user_message: str) -> Optional[str]:
        """
        Отправить запрос к LLM API и получить ответ.

        Args:
            user_message: Сообщение пользователя

        Returns:
            Ответ от LLM или None в случае ошибки
        """
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                payload = {
                    "messages": [
                        {
                            "role": "system",
                            "content": self.system_prompt,
                        },
                        {
                            "role": "user",
                            "content": user_message,
                        },
                    ],
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 500,
                }

                headers = {"Content-Type": "application/json"}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"

                async with session.post(
                    self.api_url,
                    json=payload,
                    headers=headers,
                ) as response:
                    if response.status == 200:
                        data = await response.json()

                        # Парсим ответ в зависимости от формата API
                        if "choices" in data and len(data["choices"]) > 0:
                            # OpenAI-совместимый формат
                            return data["choices"][0].get("message", {}).get("content", "").strip()
                        elif "result" in data:
                            # Некоторые LLM API используют "result"
                            return data["result"].strip()

                        logger.warning(f"Неожиданный формат ответа LLM: {data}")
                        return None

                    else:
                        error_text = await response.text()
                        logger.error(
                            f"Ошибка LLM API ({response.status}): {error_text[:200]}"
                        )
                        return None

        except asyncio.TimeoutError:
            logger.error(f"Таймаут при запросе к LLM (>{self.timeout}s)")
            return None
        except Exception as e:
            logger.error(f"Ошибка при запросе к LLM: {e}")
            return None

    async def _on_message(self, event: events.NewMessage.Event) -> None:
        """
        Обработчик входящих сообщений.

        Args:
            event: Event объект Telethon
        """
        try:
            msg = event.message

            # Проверяем, текстовое ли сообщение
            if not msg.text:
                return

            # Получаем ID чата
            chat_id = msg.peer_id.user_id if hasattr(msg.peer_id, "user_id") else msg.chat_id

            # Проверяем, должен ли обрабатываться этот чат
            if not self._should_process_chat(chat_id):
                return

            # Отправляем typing action
            await self._send_typing_action(chat_id)

            # Отправляем запрос к LLM
            llm_response = await self._query_llm(msg.text)

            if not llm_response:
                # Ошибка — отправляем стандартное сообщение об ошибке
                await event.respond(self.error_message)
                return

            # Отправляем ответ от LLM
            await event.respond(llm_response)
            logger.info(f"✓ Ответ LLM отправлен в чат {chat_id}")

        except Exception as e:
            logger.error(f"Ошибка в обработчике сообщения LLM: {e}")

    @staticmethod
    def from_config(config: Dict[str, Any], client: TelegramClient) -> Optional["LLMHandler"]:
        """
        Создать LLMHandler из конфигурации.

        Args:
            config: Словарь конфигурации с ключами:
                - enabled: bool
                - api_url: str
                - system_prompt: str
                - allowed_chat_ids: List[int]
                - api_key: Optional[str]
            client: TelegramClient для подключения

        Returns:
            LLMHandler или None если выключено
        """
        if not config.get("enabled", False):
            return None

        handler = LLMHandler(
            api_url=config.get("api_url", "http://127.0.0.1:5000/api/v1/chat/completions"),
            system_prompt=config.get("system_prompt", "Ты полезный ассистент в Telegram."),
            allowed_chat_ids=config.get("allowed_chat_ids", []),
            api_key=config.get("api_key"),
            timeout=config.get("timeout", 60),
        )

        handler.attach_to_client(client)
        return handler
