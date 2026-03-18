from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass
class Task:
    row_index: int
    id: str
    name: str
    phone: str
    tg_username: str
    description: str
    date: Optional[date]
    status: str
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row_index: int, row: dict) -> "Task":
        raw_date = row.get("дата задачи", "")
        parsed_date = None
        if raw_date:
            try:
                parsed_date = date.fromisoformat(str(raw_date).strip())
            except (ValueError, TypeError):
                parsed_date = None

        return cls(
            row_index=row_index,
            id=str(row.get("id", "")),
            name=str(row.get("Клиент", "")),
            phone=str(row.get("контакты", "")),
            tg_username=str(row.get("tg", "")),
            description=str(row.get("описание задачи", "")),
            date=parsed_date,
            status=str(row.get("статус", "active")),
            created_at=str(row.get("created_at", "")),
            updated_at=str(row.get("updated_at", "")),
        )

    def is_active(self) -> bool:
        return self.status == "active"

    def is_overdue(self, today: date) -> bool:
        if self.date is None:
            return False
        return self.date < today and self.status in ("active", "stuck")
