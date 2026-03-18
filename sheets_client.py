import re
from datetime import datetime, timezone
from typing import Optional

import gspread
from google.oauth2.service_account import Credentials

from config import CREDENTIALS_FILE, GOOGLE_SHEET_ID
from models import Task

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SHEET_NAME = "Лист1"
HEADERS = ["id", "Клиент", "контакты", "tg", "описание задачи", "дата задачи", "статус", "created_at", "updated_at"]

# Simple in-memory cache
_cache: Optional[list[dict]] = None
_cache_time: Optional[datetime] = None
CACHE_TTL_SECONDS = 30

# Singleton gspread client
_gc: Optional[gspread.Client] = None


def _invalidate_cache() -> None:
    global _cache, _cache_time
    _cache = None
    _cache_time = None


def _get_client() -> gspread.Client:
    global _gc
    if _gc is None:
        creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
        _gc = gspread.authorize(creds)
    return _gc


def _get_worksheet() -> gspread.Worksheet:
    client = _get_client()
    spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
    return spreadsheet.worksheet(SHEET_NAME)


def normalize_phone(phone: str) -> str:
    """Normalize phone to digits only, converting 8xxx to 7xxx."""
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]
    return digits


def get_all_rows() -> list[dict]:
    """Fetch all rows with TTL cache."""
    global _cache, _cache_time
    now = datetime.now(timezone.utc)
    if _cache is not None and _cache_time is not None:
        elapsed = (now - _cache_time).total_seconds()
        if elapsed < CACHE_TTL_SECONDS:
            return _cache

    ws = _get_worksheet()
    rows = ws.get_all_records(value_render_option="UNFORMATTED_VALUE")
    _cache = rows
    _cache_time = now
    return rows


def get_all_tasks() -> list[Task]:
    """Return all rows as Task objects (row_index is 1-based, header is row 1)."""
    rows = get_all_rows()
    tasks = []
    for i, row in enumerate(rows, start=2):  # data starts at row 2
        task = Task.from_row(row_index=i, row=row)
        if task.id:
            tasks.append(task)
    return tasks


def append_task(row_data: dict) -> None:
    """Append a new task row to the sheet."""
    ws = _get_worksheet()
    row = [row_data.get(h, "") for h in HEADERS]
    ws.append_row(row, value_input_option="RAW")
    _invalidate_cache()


def find_task_row(task_id: str) -> Optional[int]:
    """Return 1-based row number for a given task ID, or None."""
    ws = _get_worksheet()
    cell = ws.find(task_id, in_column=1)
    if cell:
        return cell.row
    return None


def update_task_fields(task_id: str, fields: dict) -> bool:
    """Update specific fields of a task by ID. Returns True if found and updated."""
    ws = _get_worksheet()
    row_num = find_task_row(task_id)
    if row_num is None:
        return False

    col_map = {header: idx + 1 for idx, header in enumerate(HEADERS)}
    fields["updated_at"] = datetime.now(timezone.utc).isoformat()

    for field, value in fields.items():
        if field in col_map:
            ws.update_cell(row_num, col_map[field], value)

    _invalidate_cache()
    return True


def search_tasks(query: str, field: str = "any") -> list[Task]:
    """Search tasks by phone, tg_username, or name."""
    all_tasks = get_all_tasks()
    query_lower = query.lower().strip()
    query_phone = normalize_phone(query)
    results = []

    for task in all_tasks:
        match = False
        if field in ("phone", "any"):
            stored_phone = normalize_phone(task.phone)
            if query_phone and query_phone in stored_phone:
                match = True
        if field in ("tg_username", "any") and not match:
            tg = task.tg_username.lstrip("@").lower()
            q = query_lower.lstrip("@")
            if q and q in tg:
                match = True
        if field in ("name", "any") and not match:
            if query_lower and query_lower in task.name.lower():
                match = True
        if match:
            results.append(task)

    return results
