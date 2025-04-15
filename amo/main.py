import tomllib
from fastapi import FastAPI, Request
# import json
import uvicorn
import logging

# from pydantic import BaseModel

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Загрузка конфигурации
with open("config.toml", "rb") as f:
    config = tomllib.load(f)

AMOCRM_DOMAIN = config['amo']['subdomain']
SERVICE_ID = config['amo']['id']
AUTH_TOKEN = config['amo']['auth']
PORT: int = config.get('fastapi', {}).get('port', 8000)
logger.info(f"Starting FastAPI server on port {PORT}")
app = FastAPI()

# class AmoMessage(BaseModel):
#     chat_id: str
#     message: dict

@app.post("/amo/webhook")
async def handle_webhook(request: Request):
    try:
        # Попробуем получить данные формы
        form_data = await request.form()
        if form_data:
            logger.info(f"Received FORM data: {form_data}")
            for key in form_data.keys():
                values = form_data.getlist(key)
                logger.info(f"Form key: {key}, values: {values}")
                # Явно ищем текстовые сообщения
                if any(isinstance(v, str) and ("message" in key.lower() or "text" in key.lower() or "body" in key.lower()) for v in values):
                    logger.info(f"Possible user message in {key}: {values}")
                # Также ищем 'прив' для отладки
                if any("прив" in str(v).lower() for v in values):
                    logger.info(f"Found 'прив' in {key}: {values}")
        else:
            # Если форма пуста, пробуем JSON
            data = await request.json()
            logger.info(f"Received JSON data: {data}")
    except Exception as e:
        logger.error(f"Error parsing request: {e}")
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("main:app", port=PORT, reload=True)
