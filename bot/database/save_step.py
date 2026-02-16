from sqlalchemy import select

from bot.database.models import UserProgress


async def save_step(session, telegram_id: int, step: str):
    result = await session.execute(
        select(UserProgress).filter_by(telegram_id=telegram_id)
    )
    progress = result.scalar_one_or_none()

    if progress:
        return
    else:
        progress = UserProgress(
            telegram_id=telegram_id,
            last_step=step,
            bot_name="hackbotukr"
        )
        session.add(progress)

    await session.commit()
