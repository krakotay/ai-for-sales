from sql_gpt import ask_database
import os
from agents import Agent, ModelSettings, set_default_openai_key, function_tool
from dotenv import load_dotenv
from prompt import personality_orchestrator, personality_synthesizer, qa
from openai.types.shared import Reasoning
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
set_default_openai_key(OPENAI_API_KEY)

orchestrator_agent = Agent(
    name="orchestrator_agent",
    instructions=f"""

    {personality_orchestrator}

    Вот полная копия таблицы:
    ```markdown
    {ask_database()}
    ```
    Вот список вопросов, что составил руководитель:
    ```markdown
    {qa}
    ```
    """,
    model="o3-mini",
    model_settings=ModelSettings(reasoning=Reasoning(effort='medium')),

)


synthesizer_agent = Agent(
    name="synthesizer_agent",
    instructions=f"""
    Твоя задача: переделать ответ от {orchestrator_agent.name} так, как будто отвечал человек по имени Алексей. Все carGPT нужно заменить на "Алексей". 
    
    {orchestrator_agent.name} может ошибаться. 
    Инструкции от руководителя по тому как этому менеджеру Алексею надо отвечать:
    ```markdown
    {personality_synthesizer}
    ```
    """,
    model="o3-mini",
    model_settings=ModelSettings(reasoning=Reasoning(effort='low')), 
)
