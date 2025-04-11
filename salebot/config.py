import logging
from rich.logging import RichHandler
import os
import tomllib

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

OPENAI_API_KEY: str = config['openai']['key']
TELEGRAM_BOT_TOKEN = config['telegram']['token']
logger.debug("Telegram bot token: %s", TELEGRAM_BOT_TOKEN)
logger.debug("OPENAI_API_KEY: %s", OPENAI_API_KEY)
# Пример логирования
logger.info("Configuration file loaded successfully.")

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
