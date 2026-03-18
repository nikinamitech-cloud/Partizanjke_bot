import os
from dotenv import load_dotenv

load_dotenv()

def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise ValueError(f"Отсутствует обязательная переменная окружения: {key}\n"
                         f"Скопируй .env.example в .env и заполни все поля.")
    return value

TELEGRAM_TOKEN: str = _require("TELEGRAM_TOKEN")
OPENAI_API_KEY: str = _require("OPENAI_API_KEY")
GOOGLE_SHEET_ID: str = _require("GOOGLE_SHEET_ID")
ALLOWED_USER_ID: int = int(_require("ALLOWED_USER_ID"))
CREDENTIALS_FILE: str = os.getenv("CREDENTIALS_FILE", "credentials.json")

MOSCOW_TZ = "Europe/Moscow"
DIGEST_HOUR = 8
DIGEST_MINUTE = 0

OPENAI_MODEL = "gpt-5.4"
MAX_HISTORY_MESSAGES = 40
