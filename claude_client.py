"""
OpenAI client: agentic function-calling loop with conversation history.
"""
import json
from datetime import datetime

import pytz
from openai import AsyncOpenAI

import tools as tool_module
from config import OPENAI_API_KEY, OPENAI_MODEL, MAX_HISTORY_MESSAGES, MOSCOW_TZ

_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# In-memory conversation history (single user)
_history: list[dict] = []

# ---------------------------------------------------------------------------
# Tool definitions for OpenAI function calling
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "add_task",
            "description": (
                "Добавить новую задачу-напоминание для клиента. "
                "Вызывать когда пользователь хочет создать задачу, поставить напоминание "
                "или записать follow-up с клиентом. "
                "Нужно хотя бы одно из полей: phone или tg_username."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "ФИО клиента"},
                    "phone": {"type": "string", "description": "Номер телефона с +, например +79161234567"},
                    "tg_username": {"type": "string", "description": "Telegram username без @"},
                    "description": {"type": "string", "description": "Что нужно сделать"},
                    "date": {"type": "string", "description": "Дата в формате YYYY-MM-DD"},
                },
                "required": ["name", "description", "date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_tasks",
            "description": (
                "Найти задачи по номеру телефона, Telegram username или ФИО клиента. "
                "Использовать когда пользователь хочет найти или показать задачи для конкретного человека."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Поисковый запрос: телефон, @username или фрагмент имени"},
                    "field": {
                        "type": "string",
                        "enum": ["any", "phone", "tg_username", "name"],
                        "description": "По какому полю искать. По умолчанию 'any' (все поля)",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_task",
            "description": (
                "Изменить поля существующей задачи. "
                "Использовать когда пользователь хочет обновить описание, перенести дату "
                "или пометить задачу как выполненную/зависшую. "
                "ВАЖНО: никогда не придумывай task_id. Если неизвестен — сначала вызови search_tasks."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "UUID задачи (из результата поиска)"},
                    "description": {"type": "string", "description": "Новое описание задачи"},
                    "date": {"type": "string", "description": "Новая дата в формате YYYY-MM-DD"},
                    "status": {
                        "type": "string",
                        "enum": ["active", "done", "stuck"],
                        "description": "Новый статус задачи",
                    },
                },
                "required": ["task_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_tasks",
            "description": (
                "Показать список задач с фильтрацией по статусу и/или диапазону дат. "
                "Использовать для: 'покажи задачи на сегодня', 'что просрочено', 'все активные задачи'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["active", "done", "stuck", "all"],
                        "description": "Фильтр по статусу. По умолчанию 'all'",
                    },
                    "date_from": {"type": "string", "description": "Начало диапазона дат YYYY-MM-DD (включительно)"},
                    "date_to": {"type": "string", "description": "Конец диапазона дат YYYY-MM-DD (включительно)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_task_by_id",
            "description": "Получить полную информацию о задаче по её UUID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "UUID задачи"},
                },
                "required": ["task_id"],
            },
        },
    },
]


def _build_system_prompt() -> str:
    tz = pytz.timezone(MOSCOW_TZ)
    now_moscow = datetime.now(tz)
    today_iso = now_moscow.strftime("%Y-%m-%d")
    today_ru = now_moscow.strftime("%d.%m.%Y")

    return (
        f"Ты — умный помощник менеджера по продажам. "
        f"Ты помогаешь управлять задачами по клиентам, которые хранятся в Google Таблице.\n\n"
        f"Сегодня: {today_ru} ({today_iso}). Московское время: UTC+3.\n\n"
        f"Правила:\n"
        f"- Всегда отвечай по-русски.\n"
        f"- Относительные даты (сегодня, завтра, в следующий понедельник, через неделю) "
        f"переводи в абсолютные (YYYY-MM-DD) перед вызовом функций.\n"
        f"- После изменений данных кратко подтверди действие.\n"
        f"- Показывай результаты поиска в виде карточек.\n"
        f"- Если запрос неоднозначен — задай один уточняющий вопрос.\n"
        f"- Никогда не показывай UUID пользователю напрямую, используй их только внутри функций.\n"
        f"- Если нужно изменить задачу, но ID неизвестен — сначала найди задачу через search_tasks."
    )


def _trim_history() -> None:
    global _history
    if len(_history) > MAX_HISTORY_MESSAGES:
        _history = _history[-MAX_HISTORY_MESSAGES:]


def reset_history() -> None:
    """Clear conversation history (e.g. on /start)."""
    global _history
    _history = []


async def process_message(user_text: str) -> str:
    """
    Process a user message through OpenAI with function-calling loop.
    Returns the final text response to send to the user.
    """
    global _history

    _history.append({"role": "user", "content": user_text})
    _trim_history()

    max_iterations = 10
    iteration = 0

    while iteration < max_iterations:
        iteration += 1

        response = await _client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "system", "content": _build_system_prompt()}] + _history,
            tools=TOOLS,
            tool_choice="auto",
        )

        message = response.choices[0].message
        finish_reason = response.choices[0].finish_reason

        # Append assistant message to history as dict
        msg_dict: dict = {"role": "assistant", "content": message.content}
        if message.tool_calls:
            msg_dict["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in message.tool_calls
            ]
        _history.append(msg_dict)
        _trim_history()

        if finish_reason == "stop":
            return message.content or "Готово."

        if finish_reason == "tool_calls":
            for tool_call in message.tool_calls:
                args = json.loads(tool_call.function.arguments)
                result = tool_module.dispatch(tool_call.function.name, args)
                _history.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })
            _trim_history()
            continue

        break

    return "Произошла ошибка при обработке запроса. Попробуй ещё раз."
