"""
Tool implementations called by Claude via tool_use.
Each function receives parsed kwargs from Claude and returns a plain string.
Errors are returned as strings (not raised) so Claude can relay them to the user.
"""
import uuid
from datetime import datetime, timezone

import sheets_client
from formatters import format_task_card


# ---------------------------------------------------------------------------
# Tool: add_task
# ---------------------------------------------------------------------------

def add_task(
    name: str,
    description: str,
    date: str,
    phone: str = "",
    tg_username: str = "",
) -> str:
    if not name.strip():
        return "Ошибка: не указано имя клиента."
    if not description.strip():
        return "Ошибка: не указано описание задачи."
    if not date.strip():
        return "Ошибка: не указана дата."
    if not phone.strip() and not tg_username.strip():
        return "Ошибка: необходимо указать хотя бы телефон или Telegram username."

    try:
        # Validate date format
        from datetime import date as date_cls
        date_cls.fromisoformat(date.strip())
    except ValueError:
        return f"Ошибка: неверный формат даты '{date}'. Используй YYYY-MM-DD."

    now_utc = datetime.now(timezone.utc).isoformat()
    task_id = str(uuid.uuid4())
    tg_clean = tg_username.lstrip("@") if tg_username else ""

    row_data = {
        "id": task_id,
        "Клиент": name.strip(),
        "контакты": phone.strip(),
        "tg": tg_clean,
        "описание задачи": description.strip(),
        "дата задачи": date.strip(),
        "статус": "active",
        "created_at": now_utc,
        "updated_at": now_utc,
    }

    try:
        sheets_client.append_task(row_data)
    except Exception as e:
        return f"Ошибка при сохранении в таблицу: {e}"

    phone_display = phone.strip() or "—"
    tg_display = f"@{tg_clean}" if tg_clean else "—"
    return (
        f"[ID:{task_id}] Задача добавлена!\n"
        f"👤 {name.strip()}\n"
        f"📞 {phone_display}  💬 {tg_display}\n"
        f"📝 {description.strip()}\n"
        f"📆 {date.strip()}"
    )


# ---------------------------------------------------------------------------
# Tool: search_tasks
# ---------------------------------------------------------------------------

def search_tasks(query: str, field: str = "any") -> str:
    if not query.strip():
        return "Ошибка: пустой запрос поиска."

    valid_fields = ("any", "phone", "tg_username", "name")
    if field not in valid_fields:
        field = "any"

    try:
        results = sheets_client.search_tasks(query.strip(), field)
    except Exception as e:
        return f"Ошибка при поиске: {e}"

    if not results:
        return f"Задачи по запросу «{query}» не найдены."

    cards = []
    for task in results:
        cards.append(f"[ID:{task.id}]\n{format_task_card(task)}")

    header = f"Найдено задач: {len(results)}\n"
    return header + "\n---\n".join(cards)


# ---------------------------------------------------------------------------
# Tool: edit_task
# ---------------------------------------------------------------------------

def edit_task(
    task_id: str,
    description: str = "",
    date: str = "",
    status: str = "",
) -> str:
    if not task_id.strip():
        return "Ошибка: не указан ID задачи."

    fields_to_update = {}

    if description.strip():
        fields_to_update["описание задачи"] = description.strip()

    if date.strip():
        try:
            from datetime import date as date_cls
            date_cls.fromisoformat(date.strip())
            fields_to_update["дата задачи"] = date.strip()
        except ValueError:
            return f"Ошибка: неверный формат даты '{date}'. Используй YYYY-MM-DD."

    if status.strip():
        valid_statuses = ("active", "done", "stuck")
        if status.strip() not in valid_statuses:
            return f"Ошибка: недопустимый статус '{status}'. Допустимые: active, done, stuck."
        fields_to_update["статус"] = status.strip()

    if not fields_to_update:
        return "Ошибка: не указаны поля для изменения (description, date или status)."

    try:
        found = sheets_client.update_task_fields(task_id.strip(), fields_to_update)
    except Exception as e:
        return f"Ошибка при обновлении: {e}"

    if not found:
        return f"Задача с ID {task_id} не найдена."

    changes = []
    if "описание задачи" in fields_to_update:
        changes.append(f"описание → «{fields_to_update['описание задачи']}»")
    if "дата задачи" in fields_to_update:
        changes.append(f"дата → {fields_to_update['дата задачи']}")
    if "статус" in fields_to_update:
        status_labels = {"active": "активная", "done": "выполнена", "stuck": "зависла"}
        changes.append(f"статус → {status_labels.get(fields_to_update['статус'], fields_to_update['статус'])}")

    return f"Задача обновлена: {', '.join(changes)}."


# ---------------------------------------------------------------------------
# Tool: list_tasks
# ---------------------------------------------------------------------------

def list_tasks(
    status: str = "all",
    date_from: str = "",
    date_to: str = "",
) -> str:
    try:
        all_tasks = sheets_client.get_all_tasks()
    except Exception as e:
        return f"Ошибка при получении задач: {e}"

    from datetime import date as date_cls

    filtered = []
    for task in all_tasks:
        if status != "all" and task.status != status:
            continue
        if date_from:
            try:
                df = date_cls.fromisoformat(date_from)
                if task.date and task.date < df:
                    continue
            except ValueError:
                pass
        if date_to:
            try:
                dt = date_cls.fromisoformat(date_to)
                if task.date and task.date > dt:
                    continue
            except ValueError:
                pass
        filtered.append(task)

    if not filtered:
        return "Задачи по заданным фильтрам не найдены."

    cards = []
    for task in filtered:
        cards.append(f"[ID:{task.id}]\n{format_task_card(task)}")

    return f"Найдено задач: {len(filtered)}\n\n" + "\n---\n".join(cards)


# ---------------------------------------------------------------------------
# Tool: get_task_by_id
# ---------------------------------------------------------------------------

def get_task_by_id(task_id: str) -> str:
    if not task_id.strip():
        return "Ошибка: не указан ID задачи."

    try:
        all_tasks = sheets_client.get_all_tasks()
    except Exception as e:
        return f"Ошибка при получении задач: {e}"

    for task in all_tasks:
        if task.id == task_id.strip():
            return f"[ID:{task.id}]\n{format_task_card(task)}\nСтатус: {task.status}\nСоздана: {task.created_at}"

    return f"Задача с ID {task_id} не найдена."


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

TOOL_HANDLERS = {
    "add_task": add_task,
    "search_tasks": search_tasks,
    "edit_task": edit_task,
    "list_tasks": list_tasks,
    "get_task_by_id": get_task_by_id,
}


def dispatch(tool_name: str, tool_input: dict) -> str:
    handler = TOOL_HANDLERS.get(tool_name)
    if handler is None:
        return f"Неизвестный инструмент: {tool_name}"
    try:
        return handler(**tool_input)
    except TypeError as e:
        return f"Ошибка вызова инструмента {tool_name}: {e}"
