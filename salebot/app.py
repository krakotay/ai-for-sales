from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
import bot as bot_module
import config as config_module
import subprocess

app = FastAPI()
bot_task = None

class PromptsUpdateRequest(BaseModel):
    orchestrator: str = None
    synthesizer: str = None
    qa: str = None

@app.on_event("startup")
async def startup_event():
    global bot_task
    if not bot_task or bot_task.done():
        bot_task = asyncio.create_task(bot_module.main())
    else:
        print("Бот уже запущен на старте.")


@app.post("/prompts")
async def update_prompts(req: PromptsUpdateRequest):
    updated = config_module.update_prompts_in_toml(req.model_dump(exclude_none=True))
    if not updated:
        raise HTTPException(status_code=400, detail="No prompts provided or update failed")
    # Перезагрузка процесса через pm2
    subprocess.Popen(["pm2", "restart", "salebot", "--update-env"])
    return {"status": "prompts updated"}
@app.get("/prompts")
async def get_prompts():
    return config_module.get_prompts()

# Не используйте asyncio.run/start_bot внизу!
# Запускайте сервер так:
# uvicorn salebot.app:app --reload