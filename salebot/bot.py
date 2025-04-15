import asyncio
from typing import Dict, Union
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from aiogram.enums.chat_action import ChatAction
# from aiogram import F
from sql_agents import orchestrator_agent, synthesizer_agent
from config import TELEGRAM_BOT_TOKEN, logger
from agents import (
    HandoffOutputItem,
    ItemHelpers,
    MessageOutputItem,
    Runner,
    ToolCallItem,
    ToolCallOutputItem,
    trace,
)

TIMEOUT = 0


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


# Глобальный словарь для хранения накопленных сообщений по chat_id
pending_messages: Dict[int, Dict[str, Union[str, asyncio.Task]]] = {}

# Глобальный словарь для хранения истории разговоров
conversation_history = {}


# Функция для очистки истории разговоров
def clear_conversation_history():
    conversation_history.clear()
    logger.info("История разговоров очищена")


async def send_typing_action(chat_id: int):
    """Отправляет статус 'печатает' в чат."""
    await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)


async def process_accumulated_message(chat_id: int, user_id: int):
    try:
        # Ждем 10 секунд. Если за это время не поступит новое сообщение, продолжаем.
        await asyncio.sleep(TIMEOUT)
        
        # Отправляем статус "печатает" перед обработкой
        
        # Получаем накопленный текст
        accumulated_text = pending_messages[chat_id]["text"]
        # Удаляем запись, так как сообщение обрабатывается
        del pending_messages[chat_id]
        input_items = conversation_history.get(str(chat_id)) or []
        await send_typing_action(chat_id)


        # Запускаем задачу для поддержания статуса "печатает" во время обработки
        typing_task = asyncio.create_task(maintain_typing_status(chat_id))
        
        try:
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
        finally:
            # Останавливаем задачу поддержания статуса "печатает"
            typing_task.cancel()

        # Отправляем накопленный текст в team.run и получаем ответ
    except asyncio.CancelledError:
        # Если задача была отменена (из-за нового сообщения) — просто выходим
        pass


async def maintain_typing_status(chat_id: int):
    """Поддерживает статус 'печатает' каждые 4 секунды, пока обрабатывается запрос."""
    try:
        while True:
            await send_typing_action(chat_id)
            # Статус "печатает" обычно отображается около 5 секунд, поэтому обновляем его каждые 4 секунды
            await asyncio.sleep(4)
    except asyncio.CancelledError:
        # Если задача была отменена, просто выходим
        pass


@dp.message(
    # F.chat.id.in_(admins)
)  # или @dp.message_handler() в зависимости от версии aiogram
async def message_handler(message: types.Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    user_text = message.text.strip()

    # Отправляем статус "печатает" сразу после получения сообщения
    await send_typing_action(chat_id)

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
    # Запускаем бота в режиме поллинга
    await bot.delete_webhook(drop_pending_updates=True)
    polling_task = asyncio.create_task(dp.start_polling(bot))

    # Если понадобится интеграция с кастомным webhook handler, раскомментируйте ниже:
    # webhook_handler = WebhookHandler(bot, dp)
    # webhook_handler.set_clear_conversation_history_callback(clear_conversation_history)
    # await webhook_handler.start()

    # Ждем завершения задачи поллинга
    await polling_task

# Экспортируем функцию для остановки (заглушка, остановка через отмену task)
def stop():
    pass

if __name__ == "__main__":
    print("Бот запущен. Жду сообщений...")
    import asyncio
    asyncio.run(main())
