import asyncio
import random
from aiogram import Bot
from sqlalchemy.future import select

from bot.database.db import SessionLocal
from bot.database.models import UserProgress
from bot.utils.push_utils import PUSH_MESSAGES
from bot.handlers.start import continue_keyboard


async def push_loop(bot: Bot):
    while True:
        await asyncio.sleep(10800)  # 3 години

        async with SessionLocal() as session:
            result = await session.execute(
                select(UserProgress.telegram_id).where(UserProgress.bot_name == "hackbotukr")
            )
            users = result.scalars().all()

        for user_id in users:
            # if user_id != 346457069: continue
            try:
                text = random.choice(PUSH_MESSAGES)
                await bot.send_message(user_id, text, reply_markup=continue_keyboard)
            except:
                pass
