import logging
from rich.logging import RichHandler
# from rich import print
# from dataclasses import dataclass
import json
import os
from autogen_ext.models.openai import OpenAIChatCompletionClient
from openai import OpenAI
from dotenv import load_dotenv
import sys
from autogen_core import ROOT_LOGGER_NAME
from autogen_agentchat import EVENT_LOGGER_NAME, TRACE_LOGGER_NAME

load_dotenv()
os.environ["FORCE_COLOR"] = "1"

logging.getLogger(ROOT_LOGGER_NAME).setLevel(logging.ERROR)
logging.getLogger(EVENT_LOGGER_NAME).setLevel(logging.INFO)
logging.getLogger(TRACE_LOGGER_NAME).setLevel(logging.INFO)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)



# Убедимся, что логирование использует UTF-8
logging.basicConfig(
    level=logging.NOTSET,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)

logger = logging.getLogger("rich")
logger.addHandler(RichHandler(rich_tracebacks=True, level=logging.WARNING))
# Устанавливаем поток вывода
sys.stdout.reconfigure(encoding="utf-8")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

GPT_4O = OpenAIChatCompletionClient(
    api_key=OPENAI_API_KEY, model="gpt-4o", max_tokens=1024
)
OPENAI_CLIENT = OpenAI(api_key=OPENAI_API_KEY)
# Пример логирования
logger.info("Configuration file loaded successfully.")
