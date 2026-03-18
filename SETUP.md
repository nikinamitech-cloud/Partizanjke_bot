# Запуск бота

## Что потребуется

- Python 3.11+
- Telegram аккаунт
- Anthropic API ключ
- Google аккаунт

---

## Шаг 1 — Создать Telegram бота

1. Открой @BotFather в Telegram
2. Отправь `/newbot`, задай имя и username
3. Скопируй токен — он нужен для `TELEGRAM_TOKEN`

---

## Шаг 2 — Узнать свой Telegram ID

1. Напиши @userinfobot в Telegram
2. Скопируй значение `Id:` — это `ALLOWED_USER_ID`

---

## Шаг 3 — Настроить Google Sheets

### 3.1 Создать Google Cloud Project

1. Открой [console.cloud.google.com](https://console.cloud.google.com/)
2. Создай новый проект (или используй существующий)
3. Включи APIs: **Google Sheets API** и **Google Drive API**
   - Меню → APIs & Services → Library → найди и включи оба

### 3.2 Создать Service Account

1. APIs & Services → Credentials → Create Credentials → Service Account
2. Задай любое имя, нажми Create
3. На странице Service Account → Keys → Add Key → JSON
4. Скачанный файл переименуй в `credentials.json` и положи в папку с ботом

### 3.3 Создать Google Таблицу

1. Открой [sheets.google.com](https://sheets.google.com/), создай новую таблицу
2. Переименуй лист в **Tasks** (нижняя вкладка)
3. Добавь заголовки в первую строку (ячейки A1–I1):
   ```
   id | name | phone | tg_username | description | date | status | created_at | updated_at
   ```
4. Скопируй ID таблицы из адресной строки:
   `https://docs.google.com/spreadsheets/d/ВОТ_ЭТОТ_ID/edit`
5. Нажми "Поделиться" → добавь email из `credentials.json` (поле `client_email`) с правами Редактора

---

## Шаг 4 — Настроить окружение

```bash
cp .env.example .env
```

Открой `.env` и заполни все поля:

```
TELEGRAM_TOKEN=токен_от_BotFather
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_SHEET_ID=id_таблицы
ALLOWED_USER_ID=твой_telegram_id
CREDENTIALS_FILE=credentials.json
```

---

## Шаг 5 — Установить зависимости и запустить

```bash
pip install -r requirements.txt
python bot.py
```

Бот запущен. Напиши ему в Telegram!

---

## Проверка работы

1. Напиши `/start` — бот должен ответить приветствием
2. Напиши: `Добавь задачу: Иван Иванов, +79161234567, отправить КП, завтра`
3. Открой Google Таблицу — должна появиться строка
4. Напиши: `Найди Иванов` — бот должен показать карточку задачи

---

## Дайджест

Каждый день в **8:00 по Москве** бот автоматически пришлёт:
- Задачи на сегодня
- Задачи на завтра
- Просроченные/зависшие задачи
