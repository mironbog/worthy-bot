import asyncio
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

TOKEN = os.getenv("BOT_TOKEN")  # токен от @BotFather

# Каждый вопрос: текст и варианты (текст кнопки, баллы 0-2).
# Больше баллов = больше аргументов "за" покупку.
QUESTIONS = [
    (
        "Насколько тебе это нужно?",
        [("Необходимо", 2), ("Было бы удобно", 1), ("Просто хочется", 0)],
    ),
    (
        "Есть ли уже похожая вещь?",
        [("Нет", 2), ("Есть, но старая/сломана", 1), ("Есть и работает", 0)],
    ),
    (
        "Сколько это от твоего бюджета (месяц)?",
        [("До 5%", 2), ("5–20%", 1), ("Больше 20%", 0)],
    ),
    (
        "Как давно ты об этом думаешь?",
        [("Больше месяца", 2), ("Несколько дней", 1), ("Увидел сегодня", 0)],
    ),
    (
        "Как часто будешь пользоваться?",
        [("Почти каждый день", 2), ("Раз в неделю", 1), ("Редко", 0)],
    ),
    (
        "Чем будешь платить?",
        [("Свои накопления", 2), ("Из текущих доходов", 1), ("Кредит/рассрочка", 0)],
    ),
    (
        "Что будет, если не купить?",
        [("Будут реальные проблемы", 2), ("Немного расстроюсь", 1), ("Ничего", 0)],
    ),
]

MAX_SCORE = len(QUESTIONS) * 2

# Состояние пользователей в памяти: {user_id: {"step": int, "score": int}}
sessions: dict[int, dict] = {}

dp = Dispatcher()


def keyboard(step: int) -> InlineKeyboardMarkup:
    _, options = QUESTIONS[step]
    rows = [
        [InlineKeyboardButton(text=text, callback_data=f"a:{step}:{points}")]
        for text, points in options
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def question_text(step: int) -> str:
    return f"Вопрос {step + 1}/{len(QUESTIONS)}\n\n{QUESTIONS[step][0]}"


def verdict(score: int) -> str:
    share = score / MAX_SCORE
    if share >= 0.7:
        title = "✅ Покупай"
        text = "Покупка обоснована: тебе это нужно, и она не ударит по бюджету."
    elif share >= 0.4:
        title = "⏳ Подожди неделю"
        text = (
            "Аргументы есть, но не железные. Если через неделю желание "
            "не пропадёт, покупай."
        )
    else:
        title = "❌ Не стоит"
        text = "Похоже на импульсивную покупку. Деньги лучше оставить себе."
    return f"{title}\n\n{text}\n\nРезультат: {score} из {MAX_SCORE}"


@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "Привет! Я помогу понять, стоит ли что-то покупать.\n"
        "Отвечу по ответам на несколько вопросов.\n\n"
        "Подумай о вещи, которую хочешь купить, и жми /buy"
    )


@dp.message(Command("buy"))
async def buy(message: Message):
    sessions[message.from_user.id] = {"step": 0, "score": 0}
    await message.answer(question_text(0), reply_markup=keyboard(0))


@dp.callback_query(F.data.startswith("a:"))
async def answer(callback: CallbackQuery):
    _, step_str, points_str = callback.data.split(":")
    step, points = int(step_str), int(points_str)

    session = sessions.get(callback.from_user.id)
    # Защита от повторных нажатий и устаревших кнопок
    if session is None or session["step"] != step:
        await callback.answer("Это старый вопрос. Начни заново: /buy")
        return

    session["score"] += points
    session["step"] += 1

    if session["step"] < len(QUESTIONS):
        nxt = session["step"]
        await callback.message.edit_text(question_text(nxt), reply_markup=keyboard(nxt))
    else:
        await callback.message.edit_text(verdict(session["score"]))
        await callback.message.answer("Хочешь оценить ещё что-то? Жми /buy")
        del sessions[callback.from_user.id]

    await callback.answer()


async def main():
    if not TOKEN:
        raise SystemExit("Задай переменную окружения BOT_TOKEN")
    bot = Bot(TOKEN)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
