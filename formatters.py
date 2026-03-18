"""
Formatting helpers: task cards, digest sections, message splitting.
"""
from datetime import date
from typing import Optional

import pytz

from models import Task

MONTHS_RU = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля",
    5: "мая", 6: "июня", 7: "июля", 8: "августа",
    9: "сентября", 10: "октября", 11: "ноября", 12: "декабря",
}


def format_date_ru(d: Optional[date]) -> str:
    if d is None:
        return "—"
    return f"{d.day} {MONTHS_RU[d.month]} {d.year}"


def format_task_card(task: Task, overdue_days: int = 0) -> str:
    phone = task.phone or "—"
    tg = f"@{task.tg_username}" if task.tg_username else "—"
    date_str = format_date_ru(task.date)

    lines = [
        f"👤 {task.name}",
        f"📞 {phone}  💬 {tg}",
        f"📝 {task.description}",
        f"📆 {date_str}",
    ]
    if overdue_days > 0:
        lines.append(f"⚠️ Просрочено на {overdue_days} д.")

    return "\n".join(lines)


def format_digest(
    today_tasks: list[Task],
    tomorrow_tasks: list[Task],
    overdue_tasks: list[Task],
    today_date: date,
) -> str:
    date_str = format_date_ru(today_date)

    if not today_tasks and not tomorrow_tasks and not overdue_tasks:
        return f"☀️ Доброе утро! На {date_str} задач нет. Хорошего дня!"

    sections = [f"📋 Доброе утро! Дайджест на {date_str}\n"]

    if today_tasks:
        sections.append(f"━━━━━━━━━━━━━━━━━━━\n📅 СЕГОДНЯ ({len(today_tasks)} задач)\n━━━━━━━━━━━━━━━━━━━")
        for task in today_tasks:
            sections.append(format_task_card(task))

    if tomorrow_tasks:
        sections.append(f"━━━━━━━━━━━━━━━━━━━\n📅 ЗАВТРА ({len(tomorrow_tasks)} задач)\n━━━━━━━━━━━━━━━━━━━")
        for task in tomorrow_tasks:
            sections.append(format_task_card(task))

    if overdue_tasks:
        sections.append(f"━━━━━━━━━━━━━━━━━━━\n⚠️ ПРОСРОЧЕНО ({len(overdue_tasks)} задач)\n━━━━━━━━━━━━━━━━━━━")
        for task in overdue_tasks:
            days = (today_date - task.date).days if task.date else 0
            sections.append(format_task_card(task, overdue_days=days))

    return "\n\n".join(sections)


def split_message(text: str, limit: int = 4000) -> list[str]:
    """Split long messages at double newlines to avoid breaking task cards."""
    if len(text) <= limit:
        return [text]

    parts = text.split("\n\n")
    chunks: list[str] = []
    current = ""

    for part in parts:
        candidate = (current + "\n\n" + part) if current else part
        if len(candidate) > limit:
            if current:
                chunks.append(current)
            current = part
        else:
            current = candidate

    if current:
        chunks.append(current)

    return chunks
