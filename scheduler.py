"""
APScheduler setup: daily digest at 8:00 Moscow time.
Integrated with python-telegram-bot v21 via post_init hook.
"""
import asyncio
import logging

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot
from telegram.ext import Application

from config import ALLOWED_USER_ID, DIGEST_HOUR, DIGEST_MINUTE, MOSCOW_TZ
from digest import build_digest

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


async def send_daily_digest(bot: Bot) -> None:
    """Fetch and send the morning digest to the allowed user."""
    logger.info("Отправка утреннего дайджеста...")
    try:
        parts = build_digest()
        for part in parts:
            await bot.send_message(chat_id=ALLOWED_USER_ID, text=part)
        logger.info("Дайджест отправлен успешно.")
    except Exception as e:
        logger.exception(f"Ошибка при отправке дайджеста: {e}")
        try:
            await bot.send_message(
                chat_id=ALLOWED_USER_ID,
                text=f"Не удалось сформировать дайджест: {e}"
            )
        except Exception:
            pass


async def setup_scheduler(app: Application) -> None:
    """
    Set up APScheduler and attach it to the running event loop via post_init.
    Called in bot.py: application.post_init = setup_scheduler
    """
    global _scheduler

    moscow_tz = pytz.timezone(MOSCOW_TZ)
    _scheduler = AsyncIOScheduler(timezone=moscow_tz)

    _scheduler.add_job(
        func=send_daily_digest,
        trigger="cron",
        hour=DIGEST_HOUR,
        minute=DIGEST_MINUTE,
        id="daily_digest",
        replace_existing=True,
        kwargs={"bot": app.bot},
    )

    _scheduler.start()
    logger.info(
        f"Планировщик запущен. Дайджест будет отправляться в "
        f"{DIGEST_HOUR:02d}:{DIGEST_MINUTE:02d} по Москве."
    )


async def shutdown_scheduler(app: Application) -> None:
    """Gracefully shut down scheduler on bot stop."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Планировщик остановлен.")
