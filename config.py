import logging
from rich.logging import RichHandler
from rich import print
from dataclasses import dataclass
import json
import os
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core import EVENT_LOGGER_NAME
from dotenv import load_dotenv
import sys

load_dotenv()

# Убедимся, что логирование использует UTF-8
logging.basicConfig(
    level=logging.INFO, handlers=[RichHandler(rich_tracebacks=True)], force=True
)
logger = logging.getLogger(EVENT_LOGGER_NAME)

# Устанавливаем поток вывода
sys.stdout.reconfigure(encoding="utf-8")

# Устанавливаем базовый уровень логирования
logging.basicConfig(level=logging.INFO, handlers=[RichHandler(rich_tracebacks=True)])
logger = logging.getLogger("autogen_core.events")

# Пример Trace логирования с использованием rich
logger.setLevel(logging.DEBUG)
logger.debug("Это сообщение для отладки с цветами и форматированием.")


# Пример структурированного логирования с JSON
@dataclass
class MyEvent:
    timestamp: str
    message: str


class MyHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            # if isinstance(record.msg, MyEvent):
            #     # Выводим структурированное сообщение в формате JSON
            print(json.dumps(record.msg.__dict__, indent=10, ensure_ascii=False))
        except Exception:
            self.handleError(record)


# Настроим Structured Logging
logger.setLevel(logging.INFO)
my_handler = MyHandler()
logger.addHandler(my_handler)

# Логируем структурированное сообщение
logger.info(MyEvent("2025-02-06T14:16:00", "Это структурированное лог-сообщение"))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

GPT_4O = OpenAIChatCompletionClient(
    api_key=OPENAI_API_KEY, model="gpt-4o", max_tokens=1024
)

# Пример логирования
logger.info("Configuration file loaded successfully.")
