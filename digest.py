"""
Daily digest logic: fetch tasks, categorize by date, build message.
"""
from datetime import date, datetime, timedelta

import pytz

import sheets_client
from formatters import format_digest, split_message
from models import Task
from config import MOSCOW_TZ


def get_moscow_today() -> date:
    tz = pytz.timezone(MOSCOW_TZ)
    return datetime.now(tz).date()


def build_digest() -> list[str]:
    """
    Fetch all tasks, categorize into today/tomorrow/overdue, format digest.
    Returns a list of message strings (split if too long for Telegram).
    """
    try:
        all_tasks = sheets_client.get_all_tasks()
    except Exception as e:
        return [f"Ошибка при получении задач для дайджеста: {e}"]

    today = get_moscow_today()
    tomorrow = today + timedelta(days=1)

    today_tasks: list[Task] = []
    tomorrow_tasks: list[Task] = []
    overdue_tasks: list[Task] = []

    for task in all_tasks:
        # Skip completed tasks
        if task.status == "done":
            continue

        if task.date is None:
            # Tasks without a date go to overdue if status is stuck
            if task.status == "stuck":
                overdue_tasks.append(task)
            continue

        if task.date == today and task.status == "active":
            today_tasks.append(task)
        elif task.date == tomorrow and task.status == "active":
            tomorrow_tasks.append(task)
        elif task.date < today:
            # Overdue: past due date, still active or stuck
            overdue_tasks.append(task)

    # Sort each bucket by date (oldest overdue first)
    today_tasks.sort(key=lambda t: t.date or today)
    tomorrow_tasks.sort(key=lambda t: t.date or tomorrow)
    overdue_tasks.sort(key=lambda t: t.date or today)

    message = format_digest(today_tasks, tomorrow_tasks, overdue_tasks, today)
    return split_message(message)
