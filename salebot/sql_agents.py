from sql_gpt import ask_database
from agents import Agent, set_default_openai_key
from config import OPENAI_API_KEY, OPENAI_MODEL, SYNTHESIZER_PROMPT, ORCHESTRATOR_PROMPT, QA_PROMPT
set_default_openai_key(OPENAI_API_KEY)

orchestrator_agent = Agent(
    name="orchestrator_agent",
    instructions=f"""

    {ORCHESTRATOR_PROMPT}

    Вот полная копия таблицы:
    ```markdown
    {ask_database()}
    ```
    Вот список вопросов, что составил руководитель:
    ```markdown
    {QA_PROMPT}
    ```
    """,
    model=OPENAI_MODEL,

)


synthesizer_agent = Agent(
    name="synthesizer_agent",
    instructions=f"""
    Твоя задача: переделать ответ от {orchestrator_agent.name} так, как будто отвечал человек по имени Алексей. Все carGPT нужно заменить на "Алексей". 
    
    {orchestrator_agent.name} может ошибаться. 
    Инструкции от руководителя по тому как этому менеджеру Алексею надо отвечать:
    ```markdown
    {SYNTHESIZER_PROMPT}
    ```
    """,
    model=OPENAI_MODEL,
)
