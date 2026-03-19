"""
Telegram message handlers.
"""
import asyncio
import logging

from telegram import Update
from telegram.ext import ContextTypes

import claude_client
from config import ALLOWED_USER_IDS
from formatters import split_message

logger = logging.getLogger(__name__)


async def _keep_typing(bot, chat_id: int, stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        await bot.send_chat_action(chat_id=chat_id, action="typing")
        await asyncio.sleep(4)


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id not in ALLOWED_USER_IDS:
        return

    claude_client.reset_history()
    await update.message.reply_text(
        "👋 Привет! Я твой ИИ-помощник для управления задачами по клиентам.\n\n"
        "Ты можешь:\n"
        "• Добавлять задачи в свободной форме\n"
        "• Искать задачи по имени, телефону или Telegram\n"
        "• Изменять задачи и переносить даты\n"
        "• Каждое утро в 8:00 я буду присылать дайджест\n\n"
        "Просто напиши мне, что нужно сделать!"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id not in ALLOWED_USER_IDS:
        logger.warning(f"Отклонён запрос от user_id={update.effective_user.id}")
        return

    user_text = update.message.text
    if not user_text or not user_text.strip():
        return

    # Keep showing typing indicator while Claude processes (disappears after 5s otherwise)
    stop_event = asyncio.Event()
    typing_task = asyncio.create_task(
        _keep_typing(context.bot, update.effective_chat.id, stop_event)
    )

    try:
        response_text = await claude_client.process_message(user_text)
    except Exception as e:
        logger.exception(f"Ошибка при обработке сообщения: {e}")
        response_text = None
    finally:
        stop_event.set()
        typing_task.cancel()

    if response_text is None:
        await update.message.reply_text(
            "Произошла ошибка. Попробуй ещё раз или перезапусти бота командой /start"
        )
        return

    # Split long messages and send
    parts = split_message(response_text)
    for part in parts:
        await update.message.reply_text(part)
