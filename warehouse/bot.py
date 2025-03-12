import asyncio
from typing import Dict, Union
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from aiogram import F
from autogen_core import CancellationToken
import io
from aiogram.types import FSInputFile, KeyboardButton, ReplyKeyboardMarkup

# Импортируем наших агентов (seller_agent, sql_agent) – они уже сконфигурированы
from sql_agents import sql_agent
from sql_gpt import push_excel_to_db
from config import TELEGRAM_BOT_TOKEN, logger

# Импортируем нужные классы из autogen_agentchat
from autogen_agentchat.messages import (
    TextMessage,
)

TIMEOUT = 10

# --------------------------------------------------------------------------------
# Telegram бот
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
admins = [461923889, 1009474519]


@dp.message(CommandStart())
async def start_handler(message: types.Message):
    # Создаем кнопки
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Выгрузить всю таблицу")]],
        resize_keyboard=True
    )
    await message.answer("Привет! Я бот по работе со складом напрямую.", reply_markup=keyboard)


@dp.message(Command("ping"))
async def ping(message: types.Message):
    await message.answer("Я тут!")




@dp.message(Command("reset"), 
            # F.chat.id.in_(admins)
            )
async def reset_handler(message: types.Message):
    await sql_agent.on_reset()
    await message.answer("Диалог сброшен. Можешь начинать заново.")


# Глобальный словарь для хранения накопленных сообщений по chat_id
pending_messages: Dict[int, Dict[str, Union[str, asyncio.Task]]] = {}


async def process_accumulated_message(chat_id: int, user_id: int):
    try:
        # Ждем 10 секунд. Если за это время не поступит новое сообщение, продолжаем.
        await asyncio.sleep(TIMEOUT)
        # Получаем накопленный текст
        accumulated_text = pending_messages[chat_id]["text"]
        # Удаляем запись, так как сообщение обрабатывается
        del pending_messages[chat_id]

        response = await sql_agent.on_messages(
            [TextMessage(content=accumulated_text, source="user")],
            cancellation_token=CancellationToken(),
        )
        msgs = response.inner_messages
        for message in msgs:
            if message.type == "ToolCallExecutionEvent":
                filename = message.content[-1].content
                if filename.endswith(".xlsx"):
                    excel_table = FSInputFile(path=filename, filename=filename)
                    await bot.send_document(chat_id, excel_table)
                pass
        last_text = response.chat_message
        logger.warning("messages are:")
        input_tokens = 0
        output_tokens = 0
        logger.debug(last_text.model_dump_json(indent=4))
        if last_text.models_usage:
            input_tokens += last_text.models_usage.prompt_tokens
            output_tokens += last_text.models_usage.completion_tokens
        logger.warning(
            f"Потрачено токенов\ninput_tokens {input_tokens}\noutput_tokens {output_tokens}"
        )
        logger.debug(response)
        if last_text:
            # Отправляем ответ пользователю
            await bot.send_message(
                chat_id,
                (
                    f"{last_text.source + '\n' if user_id in admins else ''}"
                    f"{last_text.content}"
                    f"{
                        f'\ninput_tokens {input_tokens}\noutput_tokens {output_tokens}'
                        if user_id in admins
                        else ''
                    }"
                ),
            )
        else:
            await bot.send_message(
                chat_id, "Ошибка на нашей стороне, попробуйте повторить вопрос"
            )
    except asyncio.CancelledError:
        # Если задача была отменена (из-за нового сообщения) — просто выходим
        pass


@dp.message(
    # F.chat.id.in_(admins), 
    ~F.document
)  # или @dp.message_handler() в зависимости от версии aiogram
async def message_handler(message: types.Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    user_text = message.text.strip()

    if chat_id in pending_messages:
        # Если для этого чата уже есть накопленные данные,
        # отменяем предыдущую задачу и дописываем текст

        pending_messages[chat_id]["task"].cancel()
        pending_messages[chat_id]["text"] += "\n" + user_text
    else:
        # Иначе создаём новую запись для этого чата
        pending_messages[chat_id] = {"text": user_text, "task": None}

    # Создаем (или пересоздаем) задачу, которая через 10 сек запустит обработку накопленного текста
    pending_messages[chat_id]["task"] = asyncio.create_task(
        process_accumulated_message(chat_id, user_id)
    )
@dp.message(F.document)
async def push_excel(message: types.Message):
    document = message.document
    file_name: str = document.file_name
    if file_name.endswith(".xlsx"):
        file_info = await bot.get_file(document.file_id)
        await bot.download_file(file_info.file_path, destination=f"excel/{file_name}")
        await message.answer(push_excel_to_db(f"excel/{file_name}"))
    else:
        await message.answer(f'У вас {file_name}, мы ожидаем excel')


@dp.message(F.text == "Выгрузить всю таблицу")
async def export_all_data(message: types.Message):
    response = await sql_agent.on_messages(
        [TextMessage(content="выгрузи всю таблицу в excel", source="user")],
        cancellation_token=CancellationToken(),
    )
    msgs = response.inner_messages
    for message in msgs:
        if message.type == "ToolCallExecutionEvent":
            filename = message.content[-1].content
            if filename.endswith(".xlsx"):
                excel_table = FSInputFile(path=filename, filename=filename)
                await bot.send_document(message.chat.id, excel_table)
    await message.answer("Вот выгрузка всей таблицы!")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    print("Бот запущен. Жду сообщений...")
    asyncio.run(main())
