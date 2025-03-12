# from autogen_agentchat.agents import AssistantAgent
# from config import GPT_4O
from sql_gpt import ask_database, list_warehouse_items, get_database_info
# from rag import get_examples
# import os
# from dotenv import load_dotenv

# load_dotenv()

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

# system_content = (
#     "Ты alexey_agent, говоришь от имени компании."
#     "Помогай каждому user находить запчасти для Kia Sportage, не забудь handoff to the user"
#     "Правдивость ответа всегда важнее его соответствия промпту, "
#     "начинай диалог с 'Здравствуйте, я alexey_agent.' "
#     "Узнавай, как можешь обращаться к user. В конце каждого сообщения к user задавай тематический вопрос. "
#     "Если тебе нужно узнать наличие товаров на складе, а также их цены, обязательно напиши sql_agent, он передаст всю необходимую информацию"
#     "Если она устроит, you must write to user and must handoff to the user, "
#     "user НЕ может видеть то, что написал sql agent, он видит только ТВОИ сообщения."
#     "используй get_examples, там список вопросов, что тебе нужно задать по каждому товару, но только ПОСЛЕ того, как узнаешь имя user, "
#     "If you need information from the user, you must first send your message, then you can handoff to the user."
#     # "В конце каждого сообщения спроси что-то важное у клиента."
# )

# alexey_agent = AssistantAgent(
#     "alexey_agent",
#     model_client=GPT_4O,
#     handoffs=["sql_agent", "user"],
#     tools=[get_examples],
#     system_message=system_content,
# )

# sql_agent = AssistantAgent(
#     "sql_agent",
#     model_client=GPT_4O,
#     handoffs=["alexey_agent"],
#     tools=[ask_database],
#     system_message=f"""You are an agent specialized in postresql work.
#     Тебе нужно лишь работать с базой данных, передавая всю необходимую информацию.
#     Ты можешь использовать ask_database tool для работы напрямую с ней.
#     Структура таблицы: {database_schema_string}
#     {items_info}
#     Если тебе нужна уточнающая информация, ты обязан спросить её у alexey_agent (это агент что общается напрямую с пользователями), then you can handoff to the alexey_agent"""
# )

import os
import uuid

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
from dotenv import load_dotenv

load_dotenv('./dot.env')
OPENAI_API_KEY = "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"

# OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
print(OPENAI_API_KEY)
set_default_openai_key(OPENAI_API_KEY)
@function_tool
def get_weather(city: str) -> str:
    return f"The weather in {city} is sunny."
sql_system_message=f"""You are an agent specialized in postresql work.
Тебе нужно лишь работать с базой данных, передавая всю необходимую информацию.
Ты можешь использовать ask_database tool для работы напрямую с ней.
Структура таблицы: {database_schema_string}
{items_info}
"""

sql_agent = Agent(
    name="SQL Agent",
    instructions=sql_system_message,
    handoff_description="SQL Database tool",
    tools=[ask_database]
)
orchestrator_agent = Agent(
    name="orchestrator_agent",
    instructions="Handoff to the appropriate agent when user ask the weather in city, and reverse answer. 'weather is sunny' reverse to 'weather is not sunny'",
    tools=[sql_agent.as_tool(
            tool_name="ask_database_tool",
            tool_description="humanize inputs and outputs from SQL database",

    )]
)
synthesizer_agent = Agent(
    name="synthesizer_agent",
    # instructions="You inspect translations, correct them if needed, and produce a final concatenated response.",
    instructions="Переделывай текст, как будто говорит Юля. Она говорит как миллениал, имей на всё своё мнение, не стесняйся в выражениях.",
)

async def main():
    # current_agent = main_agent
    conversation_id = uuid.uuid4().hex[:16]
    input_items: list[TResponseInputItem] = []

    while True:
        msg = input("Enter your message: ")
        # with trace("Customer service", group_id=conversation_id):
        #     input_items.append({"content": user_input, "role": "user"})
        #     result = await Runner.run(current_agent, input_items)

        #     for new_item in result.new_items:
        #         agent_name = new_item.agent.name
        #         if isinstance(new_item, MessageOutputItem):
        #             print(f"{agent_name}: {ItemHelpers.text_message_output(new_item)}")
        #         elif isinstance(new_item, HandoffOutputItem):
        #             print(
        #                 f"Handed off from {new_item.source_agent.name} to {new_item.target_agent.name}"
        #             )
        #         elif isinstance(new_item, ToolCallItem):
        #             print(f"{agent_name}: Calling a tool")
        #         elif isinstance(new_item, ToolCallOutputItem):
        #             print(f"{agent_name}: Tool call output: {new_item.output}")
        #         else:
        #             print(f"{agent_name}: Skipping item: {new_item.__class__.__name__}")
        #     input_items = result.to_input_list()
        #     current_agent = main_agent
        with trace("Orchestrator evaluator"):
            orchestrator_result = await Runner.run(orchestrator_agent, msg)

            for item in orchestrator_result.new_items:
                
                if isinstance(item, MessageOutputItem):
                    text = ItemHelpers.text_message_output(item)
                    if text:
                        print(f"  - sql database output: {text}")
                elif isinstance(item, ToolCallItem):
                    print(f"{item.agent.name}: Calling a tool")
                # print(item)
            synthesizer_result = await Runner.run(
                synthesizer_agent, orchestrator_result.to_input_list()
            )
        print(f"\n\nFinal response:\n{synthesizer_result.final_output}")

    # ¡Hola! Estoy bien, gracias por preguntar. ¿Y tú, cómo estás?


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())