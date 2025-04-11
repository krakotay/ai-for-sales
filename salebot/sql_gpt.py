import polars as pl
import logging  # noqa: F401
from config import logger


def ask_database():
    """
    Функция для обращения к Excel базе данных

    """
    df = pl.read_excel("shopdata.xlsx")
    logger.debug(df)
    df_md = df.to_pandas().to_markdown()
    return df_md
if __name__ == "__main__":
    db = ask_database()
