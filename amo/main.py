import tomllib
from fastapi import FastAPI, Request, HTTPException
import uvicorn
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Загрузка конфигурации
with open("config.toml", "rb") as f:
    config = tomllib.load(f)

AMOCRM_DOMAIN = config['amo']['subdomain']
SERVICE_ID = config['amo']['id']
AUTH_TOKEN = config['amo']['auth']
PORT: int = config.get('fastapi', {}).get('port', 8080)
logger.info(f"Starting FastAPI server on port {PORT}")
app = FastAPI()

@app.get("/amo/webhook")
async def hello():
    raise HTTPException(status_code=404, detail="Not Found")

@app.post("/amo/webhook")
async def handle_webhook(request: Request):
    try:
        form_data = await request.form()
        if form_data:
            # Забираем contact_id
            contact_ids = form_data.getlist("message[add][0][contact_id]")
            if contact_ids and contact_ids[0] == '29205973':
                # Это сообщение от вас
                print(form_data)
                author_names = form_data.getlist("message[add][0][author][name]")
                texts = form_data.getlist("message[add][0][text]")
                author = author_names[0] if author_names else "Unknown"
                text = texts[0] if texts else ""

                # Формируем простую таблицу
                table = (
                    "Имя       | Сообщение\n"
                    "----------|----------\n"
                    f"{author} | {text}"
                )
                logger.info("\n" + table)
            else:
                # Сообщение от кого-то другого
                logger.info("Message from another person")
        else:
            # Если пришёл JSON (редко)
            data = await request.json()
            logger.info(f"Received JSON data: {data}")
    except Exception as e:
        logger.error(f"Error parsing request: {e}")
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("main:app", port=PORT, reload=True)
