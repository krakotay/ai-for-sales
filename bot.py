# # chatgpt_sqlite_bot/bot.py
# from chatgpt_postgres import sql_chatgpt, clear_conv
# from config import TELEGRAM_BOT_TOKEN, logger
# from aiogram import Bot, Dispatcher
# import asyncio
# from aiogram.types import Message
# from aiogram.filters import Command
# from aiogram import F
# import tempfile
# from aiogram.types import FSInputFile


# admins = [461923889, 1009474519]

# bot = Bot(token=TELEGRAM_BOT_TOKEN)
# dp = Dispatcher()

# # Настройка логирования


# @dp.message(Command("start"), F.from_user.id.not_in(admins))
# async def cmd_start(message: Message):
#     await message.answer("Нет доступа")


# @dp.message(Command("start"), F.from_user.id.in_(admins))
# async def admin_start(message: Message):
#     await message.answer(
#         "Привет, админ!  Я бот для управления товарами. Просто отправь мне сообщение, и я помогу тебе"
#     )


# @dp.message(Command("clear"), F.from_user.id.in_(admins))
# async def clear_history(message: Message):
#     user_id = message.from_user.id
#     res = clear_conv(user_id)
#     await message.answer(
#         f"Очистка переписки с тобой прошла {'успешно' if res else "неуспешно"}"
#     )


# @dp.message()
# async def usual(message: Message):
#     user_id = message.from_user.id
#     try:
#         answer, df = sql_chatgpt(message.text, user_id)
#     except Exception as e:
#         logger.error(e)
#         answer = e
#     if df is not None:
#         temp_file = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
#         df.write_excel(temp_file.name)
#         excel_table = FSInputFile(path=temp_file.name, filename="data.xlsx")
#         await message.answer_document(excel_table)
#         temp_file.close()
#     await message.answer(f"{answer}")


# async def main():
#     await dp.start_polling(bot)


# if __name__ == "__main__":
#     asyncio.run(main())
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from config import TELEGRAM_BOT_TOKEN, logger
import tempfile
from aiogram.types import FSInputFile

# Предположим, что sql_chatgpt и clear_conv уже импортированы из соответствующих модулей
from chatgpt_postgres import sql_chatgpt, clear_conv

admins = [461923889, 1009474519]

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# Словари для хранения состояния по пользователям
user_buffers = {}   # user_id -> list of messages
user_tasks = {}     # user_id -> asyncio.Task

TIMEOUT = 10  # время ожидания в секундах

@dp.message(Command("start"), F.from_user.id.not_in(admins))
async def cmd_start(message: types.Message):
    await message.answer("Нет доступа")

@dp.message(Command("start"), F.from_user.id.in_(admins))
async def admin_start(message: types.Message):
    await message.answer(
        "Привет, админ! Я бот для управления товарами. Просто отправь мне сообщение, и я помогу тебе"
    )

@dp.message(Command("clear"), F.from_user.id.in_(admins))
async def clear_history(message: types.Message):
    user_id = message.from_user.id
    res = clear_conv(user_id)
    await message.answer(
        f"Очистка переписки с тобой прошла {'успешно' if res else 'неуспешно'}"
    )

async def process_user_messages(user_id: int):
    """Функция, которая вызывается по истечении таймера и обрабатывает накопленные сообщения пользователя."""
    # Объединяем сообщения через перевод строки
    messages = user_buffers.get(user_id, [])
    combined_text = "\n".join(messages)

    # Очищаем буфер и удаляем задачу из словаря
    user_buffers.pop(user_id, None)
    user_tasks.pop(user_id, None)

    # Обработка объединённого текста
    try:
        answer, df = sql_chatgpt(combined_text, user_id)
    except Exception as e:
        logger.error(e)
        answer = str(e)
        df = None

    # Отправка ответа и файла (если есть)
    if df is not None:
        temp_file = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        df.write_excel(temp_file.name)
        excel_table = FSInputFile(path=temp_file.name, filename="data.xlsx")
        await bot.send_document(chat_id=user_id, document=excel_table)
        temp_file.close()

    await bot.send_message(chat_id=user_id, text=f"{answer}")

@dp.message()
async def accumulate_messages(message: types.Message):
    user_id = message.from_user.id

    # Добавляем новое сообщение в буфер
    if user_id not in user_buffers:
        user_buffers[user_id] = []
    user_buffers[user_id].append(message.text)

    # Если есть ранее запущенная задача таймера — отменяем её
    if user_id in user_tasks:
        user_tasks[user_id].cancel()

    # Запускаем новую задачу таймера для данного пользователя
    async def timer():
        try:
            await asyncio.sleep(TIMEOUT)
            await process_user_messages(user_id)
        except asyncio.CancelledError:
            # Если таймер был отменён, просто выходим
            pass

    user_tasks[user_id] = asyncio.create_task(timer())

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
