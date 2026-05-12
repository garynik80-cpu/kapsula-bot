import asyncio
import json
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.config import settings
from bot.db import Database
from bot.services import parse_payload, score_lead, summary_from_answers, load_json

logging.basicConfig(level=getattr(logging, settings.log_level))
db = Database("kapsula.db")

QUESTIONS = [
    ("keys", "Ключи?", ["На руках", "Жду дату", "Пока не знаю"]),
    ("purpose", "Цель?", ["Для себя", "Под аренду/инвест"]),
    ("object_type", "Тип объекта?", ["Новостройка", "Вторичка"]),
    ("state", "Состояние?", ["Черновая", "White box", "Чистовая", "После застройщика", "Не знаю"]),
    ("rooms", "Сколько комнат?", ["1", "2", "3", "4+"]),
    ("deadline", "Когда хотите заехать/закончить?", ["до 2 мес", "2–4", "4–6", "позже"]),
    ("priority", "Что важнее?", ["Бюджет", "Сроки", "Контроль", "Дизайн", "Минимум участия"]),
    ("budget_level", "Какой уровень бюджета ближе?", ["Оптимально", "Баланс (середина рынка)", "Без компромиссов", "Пока не понимаю"]),
]

def kb(options, prefix="ans"):
    b = InlineKeyboardBuilder()
    for o in options:
        b.button(text=o, callback_data=f"{prefix}:{o}")
    b.adjust(2)
    return b.as_markup()

async def ask_step(message: Message, step: int):
    if step == 4:
        await message.answer("Укажите площадь в м² числом, например 57")
        return
    key, text, opts = QUESTIONS[step]
    await message.answer(text, reply_markup=kb(opts, key))

async def send_summary(message: Message, user):
    a = json.loads(user["answers"] or "{}")
    s = summary_from_answers(a)
    await message.answer(f"Понял: {s}")
    await message.answer("Что показать?", reply_markup=kb(["Показать похожие кейсы", "Примеры бюджетов", "Как мы работаем", "Записаться на созвон/встречу"], "menu"))

async def main():
    db.init()
    cases = load_json("content/cases.json")
    budgets = load_json("content/budgets.json")
    about = load_json("content/about.json")

    bot = Bot(settings.bot_token)
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def start(message: Message):
        payload = parse_payload((message.text or "").replace("/start", "").strip())
        db.upsert_user(message.from_user.id, username=message.from_user.username, source=payload.get("source"), campaign=payload.get("campaign"), name_hint=payload.get("name"), fsm_state="WELCOME")
        await message.answer("Привет! Я помощник “Капсула”. Чтобы не грузить вас, задам 4–6 коротких вопросов и подберу полезные примеры. Ок?", reply_markup=kb(["Да", "Не сейчас"], "welcome"))

    @dp.callback_query(F.data.startswith("welcome:"))
    async def welcome(call: CallbackQuery):
        ans = call.data.split(":",1)[1]
        if ans == "Не сейчас":
            db.set_followup(call.from_user.id, settings.follow_up_delay_hours)
            await call.message.answer("Когда удобнее вернуться? Я могу мягко напомнить 1 раз через 24 часа.")
            return
        db.upsert_user(call.from_user.id, fsm_state="Q0")
        await ask_step(call.message, 0)

    @dp.callback_query(F.data.regexp(r"^(keys|purpose|object_type|state|rooms|deadline|priority|budget_level):"))
    async def answer(call: CallbackQuery):
        key, val = call.data.split(":",1)
        db.save_answers(call.from_user.id, {key: val})
        user = db.get_user(call.from_user.id)
        a = json.loads(user["answers"] or "{}")
        if key == "budget_level":
            await send_summary(call.message, db.get_user(call.from_user.id))
            return
        sequence = [q[0] for q in QUESTIONS]
        nxt = sequence.index(key) + 1
        db.upsert_user(call.from_user.id, fsm_state=f"Q{nxt}")
        await ask_step(call.message, nxt)

    @dp.message(F.text.regexp(r"^\d{1,3}$"))
    async def area_input(message: Message):
        user = db.get_user(message.from_user.id)
        if user and user["fsm_state"] == "Q4":
            db.save_answers(message.from_user.id, {"area_m2": message.text})
            db.upsert_user(message.from_user.id, fsm_state="Q5")
            await ask_step(message, 5)

    @dp.callback_query(F.data.startswith("menu:"))
    async def menu(call: CallbackQuery):
        action = call.data.split(":",1)[1]
        if action == "Показать похожие кейсы":
            for c in cases[:2]:
                await call.message.answer(f"Кейс: {c['title']}\n{c['text']}\n{c.get('link','')}")
            await call.message.answer("Что ближе по уровню?", reply_markup=kb(["Оптимально", "Баланс", "Премиум"], "lvl"))
        elif action == "Примеры бюджетов":
            for b in budgets[:2]:
                await call.message.answer(f"Бюджет: {b['title']}\n{b['text']}")
            await call.message.answer("Удобнее обсудить на созвоне 10–15 минут?", reply_markup=kb(["Да", "Позже"], "call"))
        elif action == "Как мы работаем":
            await call.message.answer("\n".join(about["bullets"]))
            await call.message.answer("Удобнее обсудить на созвоне 10–15 минут?", reply_markup=kb(["Да", "Позже"], "call"))
        else:
            await call.message.answer("Выберите формат: созвон 10–15 минут / встреча в офисе / просмотр объекта", reply_markup=kb(["Созвон", "Офис", "Объект"], "step"))

    @dp.callback_query(F.data.startswith("call:"))
    async def call(call: CallbackQuery):
        ans = call.data.split(":",1)[1]
        db.save_answers(call.from_user.id, {"ready_call": ans})
        if ans == "Да":
            await call.message.answer("Когда удобно?", reply_markup=kb(["Сегодня", "Завтра", "Выберите день"], "time"))
        else:
            await call.message.answer("Ок, когда будете готовы, вернемся к обсуждению.")

    @dp.callback_query(F.data.startswith("time:"))
    async def time_choice(call: CallbackQuery):
        t = call.data.split(":",1)[1]
        db.save_answers(call.from_user.id, {"preferred_time": t})
        button = KeyboardButton(text="Поделиться номером", request_contact=True)
        kb_contact = ReplyKeyboardMarkup(keyboard=[[button]], resize_keyboard=True, one_time_keyboard=True)
        await call.message.answer("Поделитесь номером или оставьте только Telegram username текстом.", reply_markup=kb_contact)

    @dp.message(F.contact)
    async def got_contact(message: Message):
        db.upsert_user(message.from_user.id, phone=message.contact.phone_number)
        await finalize(message)

    @dp.message(F.text)
    async def text_fallback(message: Message):
        if message.text in {"Дорого", "У конкурентов дешевле", "Я подумаю", "Не сейчас", "Сравниваю варианты", "Есть своя бригада", "Не доверяю / боюсь доплат", "Напишите в WhatsApp"}:
            await message.answer("Понимаю вас, это частый вопрос.")
            await message.answer("Скажите, что важнее сравнить: сроки, прозрачность сметы или контроль? Можем коротко созвониться на 10–15 минут.")
            return

    async def finalize(message: Message):
        user = db.get_user(message.from_user.id)
        a = json.loads(user["answers"] or "{}")
        score, temp = score_lead(a)
        summary = summary_from_answers(a)
        db.create_lead(message.from_user.id, summary, score, temp, "Созвон", a.get("preferred_time", ""))
        card = (
            f"Новый лид\nsource={user['source']} campaign={user['campaign']}\n@{user['username']} phone={user['phone']}\n"
            f"{summary}\nСтрах/возражение: {a.get('objection','—')}\nscore={score} temp={temp}\nnext=Созвон\ntime={a.get('preferred_time','—')}"
        )
        await bot.send_message(settings.manager_chat_id, card)
        await message.answer("Спасибо! Я передал информацию Егору. Он свяжется в указанное время.")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
