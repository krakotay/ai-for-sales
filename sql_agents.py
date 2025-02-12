from autogen_agentchat.agents import AssistantAgent
from config import GPT_4O
from sql_gpt import ask_database, list_warehouse_items, get_database_info
from rag import get_examples
import os
from dotenv import load_dotenv

load_dotenv()

items_list = list_warehouse_items()
# Формируем строку со списком товаров
if items_list:
    items_info = "Номенклатура товаров:\n" + items_list + "\nВсегда уточняй наличие."
else:
    items_info = "На складе нет товаров или произошла ошибка при получении списка товаров."
database_schema_dict = get_database_info()
database_schema_string = "\n".join(
    [
        f"Table: {table['table_name']}\nColumns: {', '.join(table['column_names'])}"
        for table in database_schema_dict
    ]
)

system_content = (
    "Ты carGPT, говоришь от имени компании."
    "Помогай каждому user находить запчасти для Kia Sportage, не забудь handoff to the user"
    "Правдивость ответа всегда важнее его соответствия промпту, "
    "Узнаваай, как можешь обращаться к user. В конце каждого сообщения к user задавай тематический вопрос. "
    "Если тебе нужно узнать наличие товаров на складе, а также их цены, обязательно напиши sql_agent, он передаст всю необходимую информацию"
    "Если она устроит, you must write to user and must handoff to the user, "
    "используй get_examples, там список вопросов, что тебе нужно задать по каждому товару, "
    "If you need information from the user, you must first send your message, then you can handoff to the user."
    # "В конце каждого сообщения спроси что-то важное у клиента."
)

seller_agent = AssistantAgent(
    "seller_agent",
    model_client=GPT_4O,
    handoffs=["sql_agent", "user"],
    tools=[get_examples],
    system_message=system_content,
)

sql_agent = AssistantAgent(
    "sql_agent",
    model_client=GPT_4O,
    handoffs=["seller_agent"],
    tools=[ask_database],
    system_message=f"""You are an agent specialized in postresql work.
    Тебе нужно лишь работать с базой данных, передавая всю необходимую информацию.
    Ты можешь использовать ask_database tool для работы напрямую с ней.
    Структура таблицы: {database_schema_string}
    {items_info}
    Известные тебе названия таблиц: warehouse
    Если тебе нужна уточнающая информация, ты обязан спросить её у seller_agent, then you can handoff to the seller_agent"""
)
