import asyncio
import logging
import random
from aiogram import Bot
from sqlalchemy.future import select

from bot.database.db import SessionLocal
from bot.database.models import UserProgress, AccessKey
from bot.utils.push_utils import PUSH_MESSAGES
from bot.handlers.start import continue_keyboard


async def push_loop(bot: Bot):
    while True:
        await asyncio.sleep(10800)  # 3 hours

        try:
            async with SessionLocal() as session:
                result = await session.execute(
                    select(UserProgress.telegram_id)
                    .join(
                        AccessKey,
                        AccessKey.telegram_id == UserProgress.telegram_id
                    )
                    .where(
                        UserProgress.bot_name == "hackbotukr",
                        AccessKey.entered.is_(True)
                    )
                )

                users = result.scalars().all()

            for user_id in users:
                try:
                    text = random.choice(PUSH_MESSAGES)

                    await bot.send_message(
                        user_id,
                        text,
                        reply_markup=continue_keyboard
                    )

                    # небольшая пауза чтобы не словить rate limit
                    await asyncio.sleep(0.05)

                except Exception as e:
                    logging.error(f"Push error for {user_id}: {e}")

        except Exception as e:
            ogging.error(f"Push loop error: {e}")
