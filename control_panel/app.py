import gradio as gr
import httpx
import tomllib
import asyncio

# Чтение адреса и порта API бота из config.toml
CONFIG_PATH = "config.toml"
with open(CONFIG_PATH, "rb") as f:
    config = tomllib.load(f)
BOT_ADDR: str = config.get("webhook", {}).get("addr", "127.0.0.1")
BOT_PORT: int = config.get("webhook", {}).get("port", 8001)
BASE_URL: str = f"http://{BOT_ADDR}:{BOT_PORT}"


# Вкладка 1: Вкл/Выкл бота

async def start_bot():
    try:
        process = await asyncio.create_subprocess_exec(
            "pm2", "restart", "salebot", "--update-env",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode == 0:
            return f"Бот перезапущен.\n{stdout.decode().strip()}"
        else:
            return f"Ошибка при перезапуске:\n{stderr.decode().strip()}"
    except Exception as e:
        return f"Исключение при запуске команды: {e}"


async def stop_bot():
    try:
        process = await asyncio.create_subprocess_exec(
            "pm2", "stop", "salebot", "--update-env",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode == 0:
            return f"Бот остановлен.\n{stdout.decode().strip()}"
        else:
            return f"Ошибка при остановке:\n{stderr.decode().strip()}"
    except Exception as e:
        return f"Исключение при запуске команды: {e}"


# Вкладка 2: Управление промптами
async def update_prompts(orchestrator, synthesizer):
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{BASE_URL}/prompts",
                json={"orchestrator": orchestrator, "synthesizer": synthesizer},
            )
            data = resp.json()
        return f"Статус: {data.get('status', 'нет ответа')}"
    except Exception as e:
        return f"Ошибка: {e}"


async def get_prompts():
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{BASE_URL}/prompts")
            data: dict = resp.json().get("prompts", {})
            orchestrator = data.get("orchestrator", "")
            synthesizer = data.get("synthesizer", "")
            return orchestrator, synthesizer
    except Exception as e:
        return f"Ошибка: {e}", f"Ошибка: {e}"


# Интерфейс Gradio
with gr.Blocks(title="Панель управления SaleBot") as app:
    gr.Markdown("# Панель управления SaleBot")
    with gr.Tabs():
        with gr.TabItem("Вкл/Выкл бота"):
            start_btn = gr.Button("Включить бота")
            stop_btn = gr.Button("Остановить бота")
            status_box = gr.Textbox(label="Статус", interactive=False)
            start_btn.click(start_bot, outputs=status_box, show_progress=True)
            stop_btn.click(stop_bot, outputs=status_box, show_progress=True)
        with gr.TabItem("Управление промптами"):
            orchestrator_prompt_box = gr.Textbox(label="Orchestrator prompt", lines=5)
            synthesizer_prompt_box = gr.Textbox(label="Synthesizer prompt", lines=5)
            get_btn = gr.Button("Получить промпт")
            update_btn = gr.Button("Обновить промпт")
            update_status = gr.Textbox(label="Статус", interactive=False)
            update_btn.click(
                update_prompts,
                inputs=[orchestrator_prompt_box, synthesizer_prompt_box],
                outputs=update_status,
                show_progress=True,
            )
            get_btn.click(
                get_prompts,
                outputs=[orchestrator_prompt_box, synthesizer_prompt_box],
                show_progress=True,
            )

app.launch(
    server_name="127.0.0.1", server_port=8002, auth=("admin", "admin123admin!!!")
)
