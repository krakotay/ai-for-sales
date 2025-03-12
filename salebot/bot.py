import asyncio
from typing import Dict, List, Optional, Union
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from aiogram import F

from sql_agents import orchestrator_agent, synthesizer_agent
from config import TELEGRAM_BOT_TOKEN, logger
from agents import (
    Agent,
    HandoffOutputItem,
    ItemHelpers,
    MessageOutputItem,
    RunContextWrapper,
    Runner,
    ToolCallItem,
    ToolCallOutputItem,
    TResponseInputItem,
    function_tool,
    handoff,
    trace,
    set_default_openai_key
)

# Импортируем нужные классы из autogen_agentchat
TIMEOUT = 3

# Словарь для хранения состояния диалога по каждому Telegram-чату.
# Здесь мы будем сохранять последний агентский HandoffMessage (то есть сообщение,
# которое сигнализирует, что агент ожидает ввод от пользователя)
# conversation_states: dict[int, ChatMessage] = {}




# --------------------------------------------------------------------------------
# Telegram бот
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
admins = [461923889, 1009474519]


@dp.message(CommandStart())
async def start_handler(message: types.Message):
    await message.answer("Привет! Напиши, что тебя интересует. Я передам это агентам.")


@dp.message(Command("ping"))
async def ping(message: types.Message):
    await message.answer("Я тут!")


# @dp.message(Command("reset"), 
#             # F.chat.id.in_(admins)pip install openai-agents

#             )
# async def reset_handler(message: types.Message):
#     # chat_id = message.chat.id
#     # conversation_states.pop(chat_id, None)
#     await team.reset()
#     await message.answer("Диалог сброшен. Можешь начинать заново.")


# Глобальный словарь для хранения накопленных сообщений по chat_id
pending_messages: Dict[int, Dict[str, Union[str, asyncio.Task]]] = {}
conversation_history = {}

async def process_accumulated_message(chat_id: int, user_id: int):
    try:
        # Ждем 10 секунд. Если за это время не поступит новое сообщение, продолжаем.
        await asyncio.sleep(TIMEOUT)
        # Получаем накопленный текст
        accumulated_text = pending_messages[chat_id]["text"]
        # Удаляем запись, так как сообщение обрабатывается
        del pending_messages[chat_id]
        input_items = conversation_history.get(str(chat_id)) or []
        with trace("Customer service"):
            input_items.append({"content": accumulated_text, "role": "user"})
            result = await Runner.run(orchestrator_agent, input_items)

            for new_item in result.new_items:
                agent_name = new_item.agent.name
                if isinstance(new_item, MessageOutputItem):
                    print(f"{agent_name}: {ItemHelpers.text_message_output(new_item)}")
                elif isinstance(new_item, HandoffOutputItem):
                    print(
                        f"Handed off from {new_item.source_agent.name} to {new_item.target_agent.name}"
                    )
                elif isinstance(new_item, ToolCallItem):
                    print(f"{agent_name}: Calling a tool")
                elif isinstance(new_item, ToolCallOutputItem):
                    print(f"{agent_name}: Tool call output: {new_item.output}")
                else:
                    print(f"{agent_name}: Skipping item: {new_item.__class__.__name__}")
            synthesizer_result = await Runner.run(
                synthesizer_agent, result.to_input_list()
            )
            print(f"\n\nFinal response:\n{synthesizer_result.final_output}")
            input_items = synthesizer_result.to_input_list()
            conversation_history[str(chat_id)] = input_items
            await bot.send_message(chat_id, synthesizer_result.final_output)

        # Отправляем накопленный текст в team.run и получаем ответ
    except asyncio.CancelledError:
        # Если задача была отменена (из-за нового сообщения) — просто выходим
        pass


@dp.message(
    # F.chat.id.in_(admins)
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


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    print("Бот запущен. Жду сообщений...")
    asyncio.run(main())
