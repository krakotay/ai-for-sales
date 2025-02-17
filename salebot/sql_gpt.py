from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv
from urllib.parse import urlparse
import os
import sqlparse
from sqlparse.tokens import DML, DDL
import polars as pl
from config import logger



load_dotenv()

tmpPostgres = urlparse(os.getenv("DATABASE_URL"))

ENGINE = create_engine(
    f"postgresql://{tmpPostgres.username}:{tmpPostgres.password}@{tmpPostgres.hostname}{tmpPostgres.path}?sslmode=require",
    echo=True,
    pool_pre_ping=True
)

def clear_conv(user_id: int) -> bool:
    query = text("DELETE FROM conversation_history WHERE user_id = :user_id")
    try:
        with ENGINE.begin() as connection:
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
    """
    Функция для обращения к postgreSQL базе данных
        query (str): запрос.

    """

    if not is_allowed_query(query):
        logger.error("Запрос не разрешён.")
        return "Не удалось выполнить запрос: Запрос не разрешён."

    try:
        with ENGINE.begin() as conn:
            result = conn.execute(text(query))
            if result.returns_rows:
                rows = result.fetchall()
                return str(rows)
            else:
                return "Запрос выполнен успешно."
    except SQLAlchemyError as e:
        logger.error(f"Ошибка при выполнении запроса: {e}")
        return f"Не удалось выполнить запрос: {e}"



def list_warehouse_items() -> str:
    """
    Возвращает таблицу в формате Markdown со списком всех товаров (поле name) 
    и их количеством (поле value) из таблицы warehouse.
    """
    query = text("SELECT name, value FROM warehouse")
    try:
        with ENGINE.connect() as conn:
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
    
def get_table_names():
    query = text("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name <> 'conversation_history'
        ORDER BY table_name;
    """)
    try:
        with ENGINE.connect() as conn:
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
        with ENGINE.connect() as conn:
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
