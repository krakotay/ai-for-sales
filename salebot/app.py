from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
import uvicorn
import bot as bot_module
import config as config_module

app = FastAPI()

# Для хранения задачи бота
bot_task = None

class PromptsUpdateRequest(BaseModel):
    orchestrator: str = None
    synthesizer: str = None
    qa: str = None

@app.post("/start")
async def start_bot():
    global bot_task
    if bot_task and not bot_task.done():
        return {"status": "already running"}
    bot_task = asyncio.create_task(bot_module.main())
    return {"status": "started"}

@app.post("/stop")
async def stop_bot():
    global bot_task
    if not bot_task or bot_task.done():
        return {"status": "not running"}
    bot_task.cancel()
    try:
        await bot_task
    except asyncio.CancelledError:
        pass
    return {"status": "stopped"}

@app.post("/update_prompts")
async def update_prompts(req: PromptsUpdateRequest):
    # Обновить config.toml и перезагрузить config
    updated = config_module.update_prompts_in_toml(req.model_dump(exclude_none=True))
    if not updated:
        raise HTTPException(status_code=400, detail="No prompts provided or update failed")
    config_module.reload_config()
    return {"status": "prompts updated"}

if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)