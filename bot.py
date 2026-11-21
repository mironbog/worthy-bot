import asyncio
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)

TOKEN = os.getenv("BOT_TOKEN")
APP_URL = "https://mironbog.github.io/worthy-app/"

# Каждый вопрос: текст и 5 вариантов (текст кнопки, баллы 4..0).
# 4 = самый сильный аргумент "за" покупку, 0 = самый слабый.
QUESTIONS = [
    ("Насколько тебе это нужно?",
     [("Жизненно необходимо", 4), ("Очень нужно", 3), ("Было бы удобно", 2),
      ("Приятный бонус", 1), ("Просто хочется", 0)]),
    ("Есть ли уже похожая вещь?",
     [("Нет, нужно впервые", 4), ("Есть, но сломана", 3), ("Есть, но сильно устарела", 2),
      ("Есть, но чуть хуже", 1), ("Есть и отлично работает", 0)]),
    ("Сколько это от твоего бюджета за месяц?",
     [("До 3%", 4), ("3–10%", 3), ("10–25%", 2),
      ("25–50%", 1), ("Больше 50%", 0)]),
    ("Как давно ты об этом думаешь?",
     [("Больше полугода", 4), ("Пару месяцев", 3), ("Пару недель", 2),
      ("Несколько дней", 1), ("Увидел сегодня", 0)]),
    ("Как часто будешь пользоваться?",
     [("Каждый день", 4), ("Несколько раз в неделю", 3), ("Раз в неделю", 2),
      ("Раз в месяц", 1), ("Почти никогда", 0)]),
    ("Чем будешь платить?",
     [("Свободные деньги, не жалко", 4), ("Накопления, отложенные на это", 3),
      ("Из текущего дохода, впритык", 2), ("Рассрочка без процентов", 1),
      ("Кредит под процент", 0)]),
    ("Что будет, если не купить?",
     [("Будут серьёзные проблемы", 4), ("Будут неудобства", 3),
      ("Ничего страшного, но жаль", 2), ("Почти не замечу", 1),
      ("Совсем ничего", 0)]),
    ("Почему хочется купить именно сейчас?",
     [("Давно планировал, пришло время", 4), ("Старая вещь отслужила своё", 3),
      ("Подвернулась хорошая скидка", 2), ("Увидел у других или в рекламе", 1),
      ("Захотелось на эмоциях", 0)]),
    ("Насколько ты уверен в качестве?",
     [("Читал отзывы, сравнил варианты", 4), ("Читал отзывы", 3),
      ("Посмотрел бегло", 2), ("Доверился продавцу", 1),
      ("Совсем не проверял", 0)]),
    ("Можно ли вернуть или перепродать?",
     [("Вернуть без проблем", 4), ("Перепродам почти без потерь", 3),
      ("Перепродам с потерями", 2), ("Перепродать будет сложно", 1),
      ("Нет, деньги не вернуть", 0)]),
    ("Есть ли альтернатива не хуже и дешевле?",
     [("Нет, это лучший вариант", 4), ("Альтернативы заметно хуже", 3),
      ("Есть чуть хуже и чуть дешевле", 2), ("Есть почти такая же, но дешевле", 1),
      ("Есть не хуже и заметно дешевле", 0)]),
    ("Как это повлияет на твои накопления и цели?",
     [("Никак", 4), ("Почти незаметно", 3), ("Немного отложит цели", 2),
      ("Заметно сдвинет цели", 1), ("Придётся отложить важное", 0)]),
    ("Будешь ли рад этой покупке через полгода?",
     [("Точно да", 4), ("Скорее да", 3), ("Не знаю", 2),
      ("Скорее нет", 1), ("Точно нет", 0)]),
    ("Как долго ты будешь этим пользоваться?",
     [("Годами", 4), ("Около года", 3), ("Несколько месяцев", 2),
      ("Пару недель", 1), ("Один раз", 0)]),
    ("Купил бы это по полной цене, без скидки?",
     [("Да, без раздумий", 4), ("Да, но подумал бы", 3), ("Подождал бы скидки", 2),
      ("Только со скидкой 30% и больше", 1), ("Ни за что по полной цене", 0)]),
]

MAX_POINTS = 4
MAX_SCORE = len(QUESTIONS) * MAX_POINTS
BUDGET_Q = 2   # индекс вопроса про долю бюджета
PAYMENT_Q = 5  # индекс вопроса про способ оплаты

# Состояние пользователей в памяти: {user_id: {"step", "score", "answers"}}
sessions: dict[int, dict] = {}

dp = Dispatcher()


def app_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🛍 Открыть Worthy", web_app=WebAppInfo(url=APP_URL))
    ]])


def keyboard(step: int) -> InlineKeyboardMarkup:
    _, options = QUESTIONS[step]
    rows = [
        [InlineKeyboardButton(text=text, callback_data=f"a:{step}:{points}")]
        for text, points in options
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def question_text(step: int) -> str:
    return f"Вопрос {step + 1}/{len(QUESTIONS)}\n\n{QUESTIONS[step][0]}"


def progress_bar(share: float) -> str:
    filled = round(share * 10)
    return "▓" * filled + "░" * (10 - filled) + f" {round(share * 100)}%"


def verdict(score: int, answers: list[int]) -> str:
    share = score / MAX_SCORE
    bar = progress_bar(share)

    # Красный флаг: очень дорого и в кредит или рассрочку одновременно
    if answers[BUDGET_Q] <= 1 and answers[PAYMENT_Q] <= 1:
        return (
            "🚩 СТОП\n\n"
            "Дорогая покупка в кредит или рассрочку бьёт по бюджету сильнее, "
            "чем кажется. Подкопи или найди вариант подешевле.\n\n"
            f"Оценка: {bar}\n({score} из {MAX_SCORE})"
        )

    if share >= 0.8:
        title = "🔥 БЕРИ"
        text = "Это сильная покупка: нужна, продумана и не ломает бюджет. Тут нечего сомневаться."
    elif share >= 0.6:
        title = "✅ Покупай, но с головой"
        text = "Доводов за больше, чем против. Проверь цену в паре магазинов и можно оформлять."
    elif share >= 0.4:
        title = "⏳ Подожди неделю"
        text = "Аргументы есть, но не железные. Если через неделю хочется так же сильно, покупай."
    elif share >= 0.2:
        title = "🤔 Скорее не стоит"
        text = "Больше эмоций, чем пользы. Отложи деньги и вернись к вопросу через месяц."
    else:
        title = "❌ Не покупай"
        text = "Это импульс, а не потребность. Твои деньги пригодятся на что-то получше."
    return f"{title}\n\n{text}\n\nОценка: {bar}\n({score} из {MAX_SCORE})"


@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "Йоу! Я Worthy 👋\n\n"
        "Скажу честно, стоит ли твоя покупка денег. "
        f"{len(QUESTIONS)} коротких вопросов, пара минут, и в конце вердикт без воды.\n\n"
        "Открой приложение кнопкой ниже или жми /buy, чтобы пройти вопросы прямо в чате.",
        reply_markup=app_keyboard(),
    )


@dp.message(Command("app"))
async def app(message: Message):
    await message.answer("Worthy в приложении 👇", reply_markup=app_keyboard())


@dp.message(Command("buy"))
async def buy(message: Message):
    sessions[message.from_user.id] = {"step": 0, "score": 0, "answers": []}
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
    session["answers"].append(points)
    session["step"] += 1

    if session["step"] < len(QUESTIONS):
        nxt = session["step"]
        await callback.message.edit_text(question_text(nxt), reply_markup=keyboard(nxt))
    else:
        await callback.message.edit_text(verdict(session["score"], session["answers"]))
        await callback.message.answer("Ещё что-то приглянулось? Жми /buy")
        del sessions[callback.from_user.id]

    await callback.answer()


async def main():
    if not TOKEN:
        raise SystemExit("Задай переменную окружения BOT_TOKEN")
    bot = Bot(TOKEN)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
