from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
import json
from sql_agents import synthesizer_agent_json, synthesizer_agent

# Конфигурация
BASE_WEBHOOK_URL = "http://127.0.0.1:8443"
WEBHOOK_PATH = "/webhook"
WEB_SERVER_HOST = "127.0.0.1"
WEB_SERVER_PORT = 8443

# Инициализация бота и диспетчера

# Пример конфига, который будем менять
bot_config = {"mode": "default", "active": True}



class WebhookHandler:
    def __init__(self, bot: Bot, dp: Dispatcher):
        self.bot = bot
        self.dp = dp
        self.WEB_SERVER_HOST = WEB_SERVER_HOST
        self.WEB_SERVER_PORT = WEB_SERVER_PORT
        self.BASE_WEBHOOK_URL = BASE_WEBHOOK_URL
        self.WEBHOOK_PATH = WEBHOOK_PATH
        self.app = web.Application()
        webhook_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
        webhook_handler.register(self.app, path=WEBHOOK_PATH)
        self.app.router.add_post("/api/config", self.update_config)
        self.app.router.add_get("/api/config", self.get_config)
        # Добавляем новые эндпоинты для работы с настройками агента
        self.app.router.add_get("/api/agent/settings", self.get_agent_settings)
        self.app.router.add_post("/api/agent/settings", self.update_agent_settings)
        setup_application(self.app, self.dp)
        
        # Функция для очистки истории разговоров
        self.clear_conversation_history_callback = None
        
    def set_clear_conversation_history_callback(self, callback):
        """Устанавливает функцию обратного вызова для очистки истории разговоров"""
        self.clear_conversation_history_callback = callback
    
    async def start(self):
        """Асинхронный метод для запуска веб-сервера"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.WEB_SERVER_HOST, self.WEB_SERVER_PORT)
        await site.start()
        print(f"Веб-сервер запущен на http://{self.WEB_SERVER_HOST}:{self.WEB_SERVER_PORT}")
        return runner

    async def on_startup(self):
        await self.bot.set_webhook(f"{BASE_WEBHOOK_URL}{WEBHOOK_PATH}")
        
    async def get_config(self, request):
        return web.json_response(bot_config)
        
    async def update_config(self, request):
        data = await request.json()
        bot_config.update(data)
        return web.json_response({"status": "success", "config": bot_config})
    
    async def get_agent_settings(self, request):
        """Получение текущих настроек агента"""
        settings = {
            "name": synthesizer_agent_json.name,
            "personality": synthesizer_agent_json.personality,
            "qa": synthesizer_agent_json.qa
        }
        return web.json_response(settings)
    
    async def update_agent_settings(self, request):
        """Обновление настроек агента"""
        try:
            data = await request.json()
            
            # Проверяем, что в запросе есть только разрешенные поля
            allowed_fields = ["personality", "qa"]
            for field in data:
                if field not in allowed_fields:
                    return web.json_response(
                        {"status": "error", "message": f"Поле {field} не разрешено для изменения"},
                        status=400
                    )
            
            # Обновляем поля в объекте synthesizer_agent_json
            if "personality" in data:
                synthesizer_agent_json.personality = data["personality"]
            if "qa" in data:
                synthesizer_agent_json.qa = data["qa"]
            
            # Обновляем инструкции в объекте synthesizer_agent
            synthesizer_agent.instructions = synthesizer_agent_json.personality + "\n" + synthesizer_agent_json.qa
            
            # Сохраняем изменения в файл prompt.json
            with open("prompt.json", "w", encoding="utf-8") as f:
                json.dump(synthesizer_agent_json.to_dict(), f, ensure_ascii=False, indent=4)
            
            # Очищаем историю разговоров через callback
            if self.clear_conversation_history_callback:
                self.clear_conversation_history_callback()
            
            return web.json_response({
                "status": "success", 
                "message": "Настройки агента успешно обновлены",
                "settings": {
                    "name": synthesizer_agent_json.name,
                    "personality": synthesizer_agent_json.personality,
                    "qa": synthesizer_agent_json.qa
                }
            })
        except Exception as e:
            return web.json_response(
                {"status": "error", "message": f"Ошибка при обновлении настроек: {str(e)}"},
                status=500
            )


