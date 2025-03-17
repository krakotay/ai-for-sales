from sql_gpt import ask_database, list_warehouse_items, get_database_info
import os
from config import BotJson
import json
from agents import Agent, function_tool, set_default_openai_key
from dotenv import load_dotenv

load_dotenv()
items_list = list_warehouse_items()
# Формируем строку со списком товаров
if items_list:
    items_info = "Номенклатура товаров:\n" + items_list + "\nВсегда уточняй наличие."
else:
    items_info = (
        "На складе нет товаров или произошла ошибка при получении списка товаров."
    )
database_schema_dict = get_database_info()
database_schema_string = "\n".join(
    [
        f"Table: {table['table_name']}\nColumns: {', '.join(table['column_names'])}"
        for table in database_schema_dict
    ]
)


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
set_default_openai_key(OPENAI_API_KEY)


@function_tool
def get_weather(city: str) -> str:
    return f"The weather in {city} is sunny."


sql_system_message = f"""You are an agent specialized in postresql work.
Тебе нужно лишь работать с базой данных, передавая всю необходимую информацию.
Ты можешь использовать ask_database tool для работы напрямую с ней.

Структура таблицы: {database_schema_string}
{items_info}
всегда возвращай ответ со всеми столцами из таблицы, её срезом, в формате markdown.
ВСЕГДА начинай предложение со слов 'Информирую SQL Agent (и только тебя), что:\n'
"""
print(sql_system_message)
sql_agent = Agent(
    name="SQL Agent",
    instructions=sql_system_message,
    handoff_description="SQL Database tool",
    tools=[ask_database],
    model="o3-mini"

)
with open("prompt.json", "r", encoding="utf-8") as f:
    synthesizer_agent_json = BotJson(**json.load(f))

synthesizer_agent = Agent(
    name=synthesizer_agent_json.name,
    instructions=synthesizer_agent_json.personality + "\n" + synthesizer_agent_json.qa,
    model="o3-mini"
)
orchestrator_agent = Agent(
    name="orchestrator_agent",
    instructions=f"ВСЕГДА начинай предложение со слов 'Информирую {synthesizer_agent_json.name} (и только тебя), что:\n'",
    tools=[
        sql_agent.as_tool(
            tool_name="ask_database_tool",
            tool_description="humanize inputs and outputs from SQL database",
        )
    ],
    model="o3-mini"

)
