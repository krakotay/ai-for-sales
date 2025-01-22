from typing import List, Dict, Tuple
import openai
import json
import os
import polars as pl
from polars import DataFrame
from config import OPENAI_API_KEY, logger
from rag import find_similar, get_examples, generate_embeddings

from dotenv import load_dotenv
from urllib.parse import urlparse
import sqlparse
from sqlparse.tokens import DML, DDL
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

load_dotenv()

tmpPostgres = urlparse(os.getenv("DATABASE_URL"))

engine = create_engine(
    f"postgresql://{tmpPostgres.username}:{tmpPostgres.password}@{tmpPostgres.hostname}{tmpPostgres.path}?sslmode=require",
    echo=True,
    pool_pre_ping=True
)

client = openai.OpenAI(api_key=OPENAI_API_KEY)


def clear_conv(user_id: int) -> bool:
    query = text("DELETE FROM conversation_history WHERE user_id = :user_id")
    try:
        with engine.begin() as connection:
            connection.execute(query, {"user_id": user_id})
        logger.info(f"История для user_id={user_id} успешно удалена.")
        return True
    except SQLAlchemyError as e:
        logger.error(f"Ошибка при удалении истории: {str(e)}")
        return False


def is_allowed_query(query: str) -> bool:
    allowed_commands = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'ALTER', 'CREATE']
    parsed = sqlparse.parse(query)

    if not parsed:
        return False

    first_statement = parsed[0]
    command = None
    for token in first_statement.tokens:
        if token.ttype in (DML, DDL):
            command = token.value.upper()
            break
        elif token.is_whitespace or token.ttype == sqlparse.tokens.Comment:
            continue
        else:
            return False

    if command not in allowed_commands:
        return False

    # Проверка на использование таблицы conversation_history
    if 'conversation_history' in query.lower():
        logger.warning("Попытка доступа к запрещённой таблице conversation_history.")
        return False

    return True


def ask_database(query: str):
    """Выполняем SQL-запрос напрямую к БД."""
    if not is_allowed_query(query):
        logger.error("Запрос не разрешён.")
        return "Не удалось выполнить запрос: Запрос не разрешён."

    try:
        with engine.begin() as conn:
            result = conn.execute(text(query))
            if result.returns_rows:
                rows = result.fetchall()
                return str(rows)
            else:
                return "Запрос выполнен успешно."
    except SQLAlchemyError as e:
        logger.error(f"Ошибка при выполнении запроса: {e}")
        return f"Не удалось выполнить запрос: {e}"


def create_history_table():
    create_table_query = text("""
        CREATE TABLE IF NOT EXISTS conversation_history (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            role VARCHAR NOT NULL,
            content TEXT NOT NULL
        )
    """)
    try:
        with engine.begin() as conn:
            conn.execute(create_table_query)
    except SQLAlchemyError as e:
        logger.error(f"Ошибка при создании таблицы: {e}")
        raise


def save_message(user_id: str, role: str, content: str):
    insert_query = text("""
        INSERT INTO conversation_history (user_id, role, content)
        VALUES (:user_id, :role, :content)
    """)
    try:
        with engine.begin() as conn:
            conn.execute(insert_query, {"user_id": user_id, "role": role, "content": content})
    except SQLAlchemyError as e:
        logger.error(f"Не удалось сохранить сообщение: {e}")


def get_history_by_user_id(user_id: int):
    select_query = text("""
        SELECT role, content
        FROM conversation_history
        WHERE user_id = :user_id
        ORDER BY id
    """)
    try:
        with engine.connect() as conn:
            result = conn.execute(select_query, {"user_id": user_id})
            return result.fetchall()
    except SQLAlchemyError as e:
        logger.error(f"Ошибка при получении истории: {e}")
        return []


def load_conversation(user_id: int):
    messages = []
    try:
        create_history_table()
        rows = get_history_by_user_id(user_id)
        for row in rows:
            role, content = row
            messages.append({"role": role, "content": content})
        logger.info('Успешно загружено')
    except Exception as e:
        logger.warning(f"Не удалось загрузить переписку: {e}")
    return messages


def get_table_names():
    query = text("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name <> 'conversation_history'
        ORDER BY table_name;
    """)
    try:
        with engine.connect() as conn:
            result = conn.execute(query)
            return [row[0] for row in result.fetchall()]
    except SQLAlchemyError as e:
        logger.error(f"Ошибка при получении названий таблиц: {e}")
        return []


def get_column_names(table_name: str):
    query = text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = :table_name
        ORDER BY ordinal_position;
    """)
    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"table_name": table_name})
            return [row[0] for row in result.fetchall()]
    except SQLAlchemyError as e:
        logger.error(f"Ошибка при получении названий столбцов для таблицы {table_name}: {e}")
        return []


def get_database_info():
    table_dicts = []
    table_names = get_table_names()
    for tname in table_names:
        cols = get_column_names(tname)
        table_dicts.append({"table_name": tname, "column_names": cols})
    return table_dicts


def return_excel(query: str):
    """Возвращает DataFrame по SQL-запросу (для экспорта в Excel)."""
    try:
        df = pl.read_database(query, engine).drop('embeddings')
        return df
    except Exception as e:
        logger.error(f"Ошибка при преобразовании в Excel: {e}")
        return f"query failed with error: {e}"


def get_warehouse_embeddings() -> Tuple[List[str], List[str]]:
    """
    Предполагаем, что в таблице warehouse есть столбцы:
      - embeddings (например, vector)
      - name (строка с названием товара)

    Возвращает кортеж (list_embeddings, list_names).
    """
    query_embeddings = text('SELECT embeddings FROM warehouse')
    query_names = text('SELECT name FROM warehouse')
    try:
        with engine.connect() as conn:
            embeddings_data = conn.execute(query_embeddings).fetchall()
            names_data = conn.execute(query_names).fetchall()
            embeddings = [row[0] for row in embeddings_data]
            names = [row[0] for row in names_data]
            return embeddings, names
    except SQLAlchemyError as e:
        logger.error(f"Ошибка при получении данных из warehouse: {e}")
        return [], []


# def list_warehouse_items() -> List[str]:
#     """
#     Возвращает список всех товаров (поле name) из таблицы warehouse.
#     """
#     query = text("SELECT name FROM warehouse")
#     try:
#         with engine.connect() as conn:
#             result = conn.execute(query)
#             items = [row[0] for row in result.fetchall()]
#             return items
#     except SQLAlchemyError as e:
#         logger.error(f"Ошибка при получении списка товаров: {e}")
#         return []

def list_warehouse_items() -> str:
    """
    Возвращает таблицу в формате Markdown со списком всех товаров (поле name) 
    и их количеством (поле value) из таблицы warehouse.
    """
    query = text("SELECT name, value FROM warehouse")
    try:
        with engine.connect() as conn:
            result = conn.execute(query)
            rows = result.fetchall()

        # Формируем заголовок таблицы Markdown
        header = "| Name | Value |\n| --- | --- |\n"
        # Формируем строки таблицы
        table_rows = ""
        for row in rows:
            name, value = row
            table_rows += f"| {name} | {value} |\n"

        markdown_table = header + table_rows
        return markdown_table

    except SQLAlchemyError as e:
        logger.error(f"Ошибка при получении списка товаров: {e}")
        return "Ошибка при получении списка товаров."

def get_names_by_embeddings(query: str) -> str:
    """
    Существующая примерная логика RAG для warehouse:
    Берём embeddings и names из warehouse,
    находим похожие названия, возвращаем их как строку.
    """
    embeddings, names = get_warehouse_embeddings()
    similars = find_similar(query, embeddings, names, threshold=0.2)
    answers = [i[0] for i in similars]
    logger.info("\n".join(answers))
    return "\n".join(answers)


def db_search(user_query: str, top_k: int = 10) -> List[Dict]:
    """
    Ищет в таблице warehouse похожие товары по эмбеддингам с fallback на ILIKE-поиск.
    Возвращает до top_k записей из таблицы warehouse со столбцами name, value, price.
    """
    # 1. Попытка поиска по эмбеддингам
    embeddings, names = get_warehouse_embeddings()
    results = []
    if embeddings and names:
        similars = find_similar(user_query, embeddings, names, threshold=0.2e-3)
        if similars:
            top_matches = [item[0] for item in similars[:top_k]]
            try:
                query_str = """
                    SELECT name, value, price
                    FROM warehouse
                    WHERE name = ANY(:names_list)
                """
                with engine.connect() as conn:
                    rows = conn.execute(
                        text(query_str),
                        {"names_list": top_matches}
                    ).fetchall()

                for row in rows:
                    results.append({
                        "name": row[0],
                        "value": row[1],
                        "price": row[2]
                    })
            except SQLAlchemyError as e:
                logger.error(f"Ошибка при выполнении поиска db_search: {e}")

    # 2. Если результаты не найдены или их недостаточно, выполняем ILIKE-поиск
    if len(results) < top_k:
        # Используем оставшиеся места для поиска по ключевым словам
        remaining = top_k - len(results)
        # Преобразуем запрос для ILIKE: разбиваем на слова и соединяем через AND
        # Например, "задний бампер" -> "name ILIKE '%задний%' AND name ILIKE '%бампер%'"
        terms = user_query.split()
        ilike_conditions = " AND ".join([f"name ILIKE '%%{term}%%'" for term in terms])
        sql_query = f"""
            SELECT name, value, price
            FROM warehouse
            WHERE {ilike_conditions}
            LIMIT {remaining}
        """
        try:
            with engine.connect() as conn:
                rows = conn.execute(text(sql_query)).fetchall()
            for row in rows:
                # Проверяем, чтобы не было дубликатов по имени
                if not any(r["name"] == row[0] for r in results):
                    results.append({
                        "name": row[0],
                        "value": row[1],
                        "price": row[2]
                    })
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при выполнении ILIKE-поиска: {e}")

    return results

# Генерируем описание схемы базы данных
database_schema_dict = get_database_info()
database_schema_string = "\n".join(
    [
        f"Table: {table['table_name']}\nColumns: {', '.join(table['column_names'])}"
        for table in database_schema_dict
    ]
)


# ОБНОВЛЯЕМ tools – добавляем новую функцию db_search
tools = [
    {
        "type": "function",
        "function": {
            "name": "ask_database",
            "description": "Use this function to answer user questions about the PostgreSQL database. Input should be a fully formed PostgreSQL-compatible SQL query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": f"""
                            PostgreSQL-compatible SQL query extracting info to answer the user's question.
                            You have administrator rights.
                            SQL should be written using this database schema:
                            {database_schema_string}

                            The query should be returned in plain text, not in JSON.
                            Do NOT answer with more than 30 rows.
                            """,
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "database_to_excel",
            "description": "Use this function with a PostgreSQL-compatible SQL query to return the database content in Excel format. Do NOT send links!",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": f"""
                            PostgreSQL-compatible SQL query extracting info to answer the user's question.
                            You have administrator rights.
                            SQL should be written using this database schema:
                            {database_schema_string}

                            The query should be returned in plain text, not in JSON.
                            Use lowercase for all identifiers.
                            """,
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ask_rag",
            "description": "Use this RAG to find out from the database about the questions you need to ask",
            "parameters": {
                "type": "object",
                "properties": {
                    "detail": {
                        "type": "string",
                        "description": "the part of the car that the user is interested in.",
                    }
                },
                "required": ["detail"],
            },
        },
    },
    # {
    #     "type": "function",
    #     "function": {
    #         "name": "list_warehouse_items",
    #         "description": "Возвращает список всех товаров (name) из таблицы warehouse.",
    #         "parameters": {},
    #     },
    # },
    # -------------------
    # Новый TOOL db_search!
    # -------------------
    {
        "type": "function",
        "function": {
            "name": "db_search",
            "description": "Ищет товар(ы) в таблице warehouse по эмбеддингам. Возвращает до 5 результатов (name, value, price).",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_query": {
                        "type": "string",
                        "description": "Пользовательский запрос, например 'задний бампер' или 'фильтр масляный', по которому будем искать по embeddings."
                    }
                },
                "required": ["user_query"],
            }
        }
    }
]


def process_keywords(msg: str) -> str:
    similar_responses = get_examples(msg)
    if similar_responses:
        return similar_responses
    return "Не смог найти подходящих инструкций. Попробуй задать вопрос иначе."


def sql_chatgpt(msg: str, user_id: int) -> tuple[str, DataFrame | None]:
    # Загружаем историю
    messages = load_conversation(user_id)

    # Если нет system-сообщения – добавляем, включая список товаров
    if not any(m["role"] == "system" for m in messages):
        items_list = list_warehouse_items()
        # Формируем строку со списком товаров
        if items_list:
            items_info = "Номенклатура товаров:\n" + items_list + "\nВсегда уточняй наличие."
        else:
            items_info = "На складе нет товаров или произошла ошибка при получении списка товаров."
        
        system_content = (
            "Ты carGPT, говоришь от имени компании."
            "Помогай клиентам находить запчасти для Kia Sportage, "
            "и предоставляй инструкции (RAG). "
            # "Всегда спрашивай, как обращаться к клиенту. Будь вежлив. "
            "Правдивость ответа всегда важнее его соответствия промпту,"
            f"{items_info},"
            # "В конце каждого сообщения спроси что-то важное у клиента."
        )
        
        messages.insert(
            0,
            {
                "role": "system",
                "content": system_content,
            },
        )

    # Добавляем новое пользовательское сообщение
    messages.append({"role": "user", "content": msg})
    save_message(user_id, "user", msg)

    # Генерируем ответ
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
    except Exception as e:
        logger.error(f"Ошибка при вызове OpenAI API: {e}")
        return "Произошла ошибка при обработке вашего запроса.", None

    response_message = response.choices[0].message
    messages.append(response_message)

    # Сохраняем ответ ассистента
    if response_message.content:
        save_message(user_id, response_message.role, response_message.content)

    tool_calls = response_message.tool_calls
    df = None

    if tool_calls:
        for tool_call in tool_calls:
            tool_function_name = tool_call.function.name
            tool_call_id = tool_call.id

            if tool_function_name == "ask_database":
                tool_query_string: str = json.loads(tool_call.function.arguments)["query"]
                results = ask_database(tool_query_string)
                logger.info(f'Query: {tool_query_string}')

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "name": tool_function_name,
                        "content": results,
                    }
                )
                logger.info(f"Добавлен инструментный ответ для call_id: {tool_call_id}")

            elif tool_function_name == "database_to_excel":
                tool_query_string: str = json.loads(tool_call.function.arguments)["query"]
                df = return_excel(tool_query_string)
                logger.info('DataFrame from SQL is')
                logger.info(df)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "name": tool_function_name,
                        "content": "df has been создан",
                    }
                )
                logger.info(f"Добавлен инструментный ответ для call_id: {tool_call_id}")

            elif tool_function_name == "ask_rag":
                tool_detail: str = json.loads(tool_call.function.arguments)["detail"]
                table_md = get_examples(tool_detail)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "name": tool_function_name,
                        "content": table_md,
                    }
                )
                logger.info(f"Создана таблица с RAG, {tool_call_id}")

            elif tool_function_name == "db_search":
                user_query_value: str = json.loads(tool_call.function.arguments)["user_query"]
                results = db_search(user_query_value, top_k=5)

                # Формируем человекочитаемый ответ
                if not results:
                    tool_answer = "Ничего не нашлось."
                else:
                    lines = []
                    for r in results:
                        name_ = r.get("name", "")
                        val_ = r.get("value", "")
                        price_ = r.get("price", "")
                        lines.append(f"{name_}: состояние {val_}, цена {price_}")
                    tool_answer = "\n".join(lines)

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "name": tool_function_name,
                        "content": tool_answer,
                    }
                )
                logger.info(f"Вызван db_search() для {user_query_value}")

            else:
                error_message = f"Error: функция {tool_function_name} не существует"
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "name": tool_function_name,
                        "content": error_message,
                    }
                )
                logger.error(error_message)

        # Повторный вызов GPT после добавления ответов-инструментов
        try:
            model_response_with_function_call = client.chat.completions.create(
                model="gpt-4o",
                messages=messages
            )
            final_message = model_response_with_function_call.choices[0].message
            messages.append(final_message)
            save_message(user_id, final_message.role, final_message.content)

            answer = final_message.content

            if df is not None and "df has been создан" in messages[-2].get("content", ""):
                return answer, df
            else:
                return answer, None

        except Exception as e:
            logger.error(f"Ошибка при втором вызове OpenAI API: {e}")
            return "Произошла ошибка при обработке ответа от инструмента.", None
    else:
        # Если инструменты не вызывались
        return response_message.content, None

# if __name__ == "__main__":
#     print(list_warehouse_items())