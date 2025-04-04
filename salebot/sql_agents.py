from sql_gpt import ask_database
import os
from agents import Agent, set_default_openai_key
from dotenv import load_dotenv
from prompt import personality, qa

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
set_default_openai_key(OPENAI_API_KEY)


orchestrator_agent = Agent(
    name="orchestrator_agent",
    instructions=f"""
    Ты carGPT, ии агент в компании, что продаёт детали для автомобилей. Вот таблица с деталями:
    ```markdown
    {ask_database()}
    ```
    Вот примерный список вопросов, что составил руководитель:
    ```markdown
    {qa}
    ```
    Некоторые из вопросов-ответов могут быть не актуальны по отношению к таблице с деталями.
    Сначала называй клиенту цену, а потом сообщай про наличие.

    """,
    model="o3-mini",
)


synthesizer_agent = Agent(
    name="synthesizer_agent",
    instructions=f"""
    Твоя задача: переделать ответ от {orchestrator_agent.name} так, как будто отвечал реальный менеджер по продажам Алексей.
    {orchestrator_agent.name} может ошибаться. 
    Инструкции от руководителя по тому как этому менеджеру Алексею надо отвечать:
    ```markdown
    {personality}
    ```
    """,
    model="o3-mini",
)
