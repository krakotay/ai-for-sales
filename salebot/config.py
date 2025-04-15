import logging
from rich.logging import RichHandler
import os
import tomllib
import toml
from typing import Dict

with open("config.toml", "rb") as f:
    config = tomllib.load(f)
os.environ["FORCE_COLOR"] = "1"

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
# sys.stdout.reconfigure(encoding="utf-8")

OPENAI_API_KEY: str = config.get('openai', {}).get('key', "")
OPENAI_MODEL: str = config.get('openai', {}).get('model', "")

TELEGRAM_BOT_TOKEN: str = config.get('telegram', {}).get('token', "")
ORCHESTRATOR_PROMPT: str = config.get('prompt', {}).get('orchestrator', "")
SYNTHESIZER_PROMPT: str = config.get('prompt', {}).get('synthesizer', "")
QA_PROMPT: str = config.get('prompt', {}).get('qa', "")
logger.debug("Telegram bot token: %s", TELEGRAM_BOT_TOKEN)
logger.debug("OPENAI_API_KEY: %s", OPENAI_API_KEY)
# Пример логирования
logger.info("Configuration file loaded successfully.")

# --- Добавлено для webhook управления ---
def update_prompts_in_toml(prompts: Dict[str, str]) -> bool:
    """Обновляет промпты в config.toml"""
    if not prompts:
        return False
    try:
        with open("config.toml", "rb") as f:
            current = tomllib.load(f)
        current.setdefault("prompt", {})
        for k, v in prompts.items():
            current["prompt"][k] = v
        with open("config.toml", "wb") as f:
            toml.dump(current, f)
        return True
    except Exception as e:
        logger.error(f"Не удалось обновить config.toml: {e}")
        return False

def reload_config():
    """Перезагружает конфиг из config.toml"""
    global config, OPENAI_API_KEY, OPENAI_MODEL, TELEGRAM_BOT_TOKEN, ORCHESTRATOR_PROMPT, SYNTHESIZER_PROMPT, QA_PROMPT
    with open("config.toml", "rb") as f:
        config = tomllib.load(f)
    OPENAI_API_KEY = config.get('openai', {}).get('key', "")
    OPENAI_MODEL = config.get('openai', {}).get('model', "")
    TELEGRAM_BOT_TOKEN = config.get('telegram', {}).get('token', "")
    ORCHESTRATOR_PROMPT = config.get('prompt', {}).get('orchestrator', "")
    SYNTHESIZER_PROMPT = config.get('prompt', {}).get('synthesizer', "")
    QA_PROMPT = config.get('prompt', {}).get('qa', "")
    logger.info("Configuration reloaded from config.toml")

class BotJson:
    name: str
    qa: str
    personality: str
    
    def __init__(self, name: str, qa: str, personality: str):
        self.name = name
        self.qa = qa
        self.personality = personality
    
    def to_dict(self):
        return {
            "name": self.name,
            "qa": self.qa,
            "personality": self.personality
        }
