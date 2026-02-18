import sys
import os
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import TOKEN
from bot.database.db import init_db

# Хендлеры
from bot.handlers.admin_handlers import router as admin_router
from bot.handlers.webmaster_create import router as wm_create_router
from bot.handlers.webmaster_invites import router as wm_invites_router
from bot.handlers.webmaster_links import router as wm_links_router
from bot.handlers.webmaster_manage import router as wm_manage_router
from bot.handlers.start import router as start_router  # <-- в самый низ
from bot.utils.push_scheduler import push_loop

# Логирование
logging.basicConfig(level=logging.INFO)

# Добавляем путь к корню проекта (если нужно)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# FSM
storage = MemoryStorage()
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=storage)


async def on_startup():
    print("Бот запущен!")
    logging.info("Бот успешно запущен!")
    await init_db()


async def main():
    await on_startup()

    logging.info("Подключаем маршрутизаторы...")
    try:
        dp.include_router(admin_router)
        logging.info("✅ admin_handlers подключён")

        dp.include_router(wm_create_router)
        logging.info("✅ webmaster_create подключён")

        dp.include_router(wm_invites_router)
        logging.info("✅ webmaster_invites подключён")

        dp.include_router(wm_links_router)
        logging.info("✅ webmaster_links подключён")

        dp.include_router(wm_manage_router)
        logging.info("✅ webmaster_manage подключён")

        dp.include_router(start_router)  # ← подключаем ПОСЛЕДНИМ
        logging.info("✅ start_router подключён (последним)")

        logging.info("🎯 Все маршрутизаторы успешно подключены")
    except Exception as e:
        logging.error(f"❌ Ошибка при подключении маршрутизаторов: {str(e)}")

    push_task = asyncio.create_task(push_loop(bot))
    try:
        await dp.start_polling(bot)
    finally:
        push_task.cancel()
        try:
            await push_task
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    asyncio.run(main())
