import asyncio
from typing import Dict, List, Optional, Union
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from aiogram import F

from sql_agents import alexey_agent, sql_agent
from config import TELEGRAM_BOT_TOKEN, logger

# Импортируем нужные классы из autogen_agentchat
from autogen_agentchat.teams import Swarm
from autogen_agentchat.conditions import HandoffTermination
from autogen_agentchat.messages import HandoffMessage, ChatMessage, TextMessage

TIMEOUT = 3

termination = HandoffTermination(target="user")

# Инициализируем команду (swarm) с нашими агентами
team = Swarm([alexey_agent, sql_agent], termination_condition=termination)

# Словарь для хранения состояния диалога по каждому Telegram-чату.
# Здесь мы будем сохранять последний агентский HandoffMessage (то есть сообщение,
# которое сигнализирует, что агент ожидает ввод от пользователя)
# conversation_states: dict[int, ChatMessage] = {}


def get_last_text_message(
    messages: List[ChatMessage], bot_name=alexey_agent.name
) -> Optional[TextMessage]:
    candidates = [
        msg
        for msg in messages
        if isinstance(msg, TextMessage) and msg.source == bot_name
    ]
    logger.warning("There're candidates!")
    logger.warning(candidates)
    if len(candidates) >= 2:
        return candidates[-2]  # предпоследнее сообщение
    elif candidates:
        return candidates[-1]  # только одно сообщение, возвращаем его
    return None  # ни одного сообщения не найдено


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


@dp.message(Command("reset"), F.chat.id.in_(admins))
async def reset_handler(message: types.Message):
    # chat_id = message.chat.id
    # conversation_states.pop(chat_id, None)
    await team.reset()
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

        # Отправляем накопленный текст в team.run и получаем ответ
        task_result = await team.run(
            task=HandoffMessage(
                source="user", target=alexey_agent.name, content=accumulated_text
            )
        )
        last_text = get_last_text_message(task_result.messages)
        logger.warning("messages are:")
        input_tokens = 0
        output_tokens = 0
        for msg in task_result.messages:
            logger.debug(msg.model_dump_json(indent=4))
            if msg.models_usage:
                input_tokens += msg.models_usage.prompt_tokens
                output_tokens += msg.models_usage.completion_tokens
        logger.warning(
            f"Потрачено токенов\ninput_tokens {input_tokens}\noutput_tokens {output_tokens}"
        )
        # logger.debug(json.dumps(task_result.messages.__dict__, ensure_ascii=False, indent=5))
        if last_text:
            # Отправляем ответ пользователю
            await bot.send_message(
                chat_id,
                (
                    f"{last_text.source + "\n" if user_id in admins else ''}"
                    f"{last_text.content.replace('alexey_agent', "Алексей")}"
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
    F.chat.id.in_(admins)
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
