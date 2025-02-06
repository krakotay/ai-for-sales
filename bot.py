import asyncio
from typing import List
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Импортируем наших агентов (seller_agent, sql_agent) – они уже сконфигурированы
from sql_agents import seller_agent, sql_agent
from config import TELEGRAM_BOT_TOKEN, logger

# Импортируем нужные классы из autogen_agentchat
from autogen_agentchat.teams import Swarm
from autogen_agentchat.conditions import HandoffTermination
from autogen_agentchat.messages import HandoffMessage, ChatMessage, TextMessage

termination = HandoffTermination(target="user")

# Инициализируем команду (swarm) с нашими агентами
team = Swarm([seller_agent, sql_agent], termination_condition=termination)

# Словарь для хранения состояния диалога по каждому Telegram-чату.
# Здесь мы будем сохранять последний агентский HandoffMessage (то есть сообщение,
# которое сигнализирует, что агент ожидает ввод от пользователя)
# conversation_states: dict[int, ChatMessage] = {}


def get_last_text_message(messages: List[ChatMessage]) -> TextMessage:
    """
    Функция проходит по списку сообщений (от последнего к первому) и возвращает первое
    встретившееся сообщение типа TextMessage.
    """
    for msg in reversed(messages):
        if isinstance(msg, TextMessage):
            return msg
    return None  # если такого сообщения нет (хотя, как правило, оно должно быть)


# --------------------------------------------------------------------------------
# Telegram бот
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def start_handler(message: types.Message):
    # chat_id = message.chat.id
    # При команде /start сбрасываем состояние (старую сессию) и начинаем новый диалог
    # conversation_states.pop(chat_id, None)
    await message.answer("Привет! Напиши, что тебя интересует. Я передам это агентам.")


@dp.message(Command("reset"))
async def reset_handler(message: types.Message):
    # chat_id = message.chat.id
    # conversation_states.pop(chat_id, None)
    team.reset()
    await message.answer("Диалог сброшен. Можешь начинать заново.")


@dp.message()
async def message_handler(message: types.Message):
    # chat_id = message.chat.id
    user_text = message.text.strip()

    task_result = await team.run(
        task=HandoffMessage(
            source="user", target=seller_agent.name, content=user_text
        )
    )
    last_text = get_last_text_message(task_result.messages)
    await message.answer(f"{last_text.source}: {last_text.content}")



async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    print("Бот запущен. Жду сообщений...")
    asyncio.run(main())
