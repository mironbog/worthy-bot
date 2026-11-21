import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)

TOKEN = os.getenv("BOT_TOKEN")
APP_URL = "https://mironbog.github.io/worthy-app/"

dp = Dispatcher()


def app_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🛍 Открыть Worthy", web_app=WebAppInfo(url=APP_URL))
    ]])


@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "Йоу! Я Worthy 👋\n\n"
        "Скажу честно, стоит ли твоя покупка денег. "
        "15 коротких вопросов, пара минут, и в конце вердикт без воды.\n\n"
        "Жми кнопку ниже 👇",
        reply_markup=app_keyboard(),
    )


@dp.message(Command("buy", "app"))
async def app(message: Message):
    await message.answer("Что-то приглянулось? Открывай Worthy 👇", reply_markup=app_keyboard())


async def main():
    if not TOKEN:
        raise SystemExit("Задай переменную окружения BOT_TOKEN")
    bot = Bot(TOKEN)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
