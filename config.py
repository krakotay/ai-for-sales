# chatgpt_sqlite_bot/config.py
import os
from dotenv import load_dotenv
import logging
import openai

load_dotenv()
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
OPENAI_CLIENT = openai.OpenAI(api_key=OPENAI_API_KEY)