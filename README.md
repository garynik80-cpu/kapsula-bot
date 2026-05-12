# kapsula-bot (MVP)

Telegram-бот для квалификации лидов компании «Капсула» на `Python + aiogram 3.x`.

## Что умеет MVP
- Принимает `/start` и deep link payload (`source/campaign/name`, plain/base64).
- Проводит короткую квалификацию (FSM, 6–8 шагов).
- Формирует summary и скоринг (Hot/Warm/Cold).
- Показывает контент-карточки: кейсы/бюджеты/как работаем.
- Обрабатывает базовые возражения короткими репликами.
- Закрывает на следующий шаг (созвон) + просит контакт.
- Отправляет карточку лида менеджеру в Telegram.
- Хранит контекст в SQLite (`users/sessions/leads`).
- Подготовлен флаг `ENABLE_SHEETS` для интеграции с Google Sheets.

## Структура
```
.
├── bot
│   ├── config.py
│   ├── db.py
│   ├── main.py
│   └── services.py
├── content
│   ├── about.json
│   ├── budgets.json
│   ├── cases.json
│   └── faq.json
├── .env.example
├── requirements.txt
└── README.md
```

## Запуск локально
1. Python 3.11+
2. Установить зависимости:
   ```bash
   pip install -r requirements.txt
   ```
3. Создать `.env` из примера:
   ```bash
   cp .env.example .env
   ```
4. Заполнить `BOT_TOKEN`, `MANAGER_CHAT_ID`.
5. Старт:
   ```bash
   python -m bot.main
   ```

## Deep link
Формат:
- `t.me/<bot>?start=source=sms|campaign=may1|name=Ivan`
- или base64 от этой строки.

## Переменные окружения
- `BOT_TOKEN`
- `MANAGER_CHAT_ID`
- `DATABASE_URL`
- `ENABLE_SHEETS`
- `GOOGLE_SHEETS_ID`
- `GOOGLE_SERVICE_ACCOUNT_FILE`
- `FOLLOW_UP_DELAY_HOURS`
- `MAX_FOLLOWUPS`
- `LOG_LEVEL`

## Контент
Хранится в `/content`:
- `cases.json` — кейсы с тегами
- `budgets.json` — примеры бюджетов
- `about.json` — блок «как работаем»
- `faq.json` — краткий FAQ

## Что заменить перед продом
- `https://example.com/case1`, `case2` на реальные ссылки/фото.
- Тексты кейсов/бюджетов под ваши реальные объекты.
- Добавить полноценный планировщик follow-up (cron/apscheduler/queue worker).
- Включить и реализовать запись в Google Sheets при `ENABLE_SHEETS=true`.

## Деплой на сервер
- Linux VM + `venv` + `systemd` сервис.
- Переменные в `.env` или секрет-хранилище.
- Запуск процесса `python -m bot.main` под отдельным пользователем.
