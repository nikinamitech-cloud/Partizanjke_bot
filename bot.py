"""
Entry point: initializes Telegram Application, registers handlers, starts scheduler.
"""
import logging

from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

from config import TELEGRAM_TOKEN
from handlers import handle_message, handle_start
from scheduler import setup_scheduler, shutdown_scheduler

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("Запуск бота...")

    app = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)
        .post_init(setup_scheduler)
        .post_shutdown(shutdown_scheduler)
        .build()
    )

    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Бот запущен. Ожидание сообщений...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    import asyncio
    asyncio.set_event_loop(asyncio.new_event_loop())
    main()
