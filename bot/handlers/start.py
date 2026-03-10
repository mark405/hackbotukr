import asyncio
import csv
import logging
import os

from aiogram import Bot, Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, WebAppInfo
from sqlalchemy.future import select

from bot.config import WEBAPP_BASE_URL, REGISTRATION_URL
from bot.database.db import SessionLocal
from bot.database.models import User, Referral, ReferralInvite, UserProgress, AccessKey
from bot.database.save_step import save_step

router = Router()
awaiting_ids = {}
awaiting_keys = {}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # директория этого скрипта
CSV_PATH = os.path.join(BASE_DIR, "users.csv")

def load_allowed_users(file_path: str) -> set[int]:
    users = set()

    with open(file_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if row:
                users.add(int(row[0]))

    return users

ALLOWED_USER_IDS = load_allowed_users(CSV_PATH)
# --- Клавиатуры ---

continue_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Продовжити", callback_data="continue_flow")]
    ]
)

how_it_works_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🔥 Дізнатись, як це працює", callback_data="how_it_works")],
        [InlineKeyboardButton(text="🆘 Допомога", callback_data="help")]
    ]
)

instruction_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Отримати доступ до інструкції", callback_data="get_instruction")],
        [InlineKeyboardButton(text="🆘 Допомога", callback_data="help")]
    ]
)

reg_inline_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🔗 ПОСИЛАННЯ ДЛЯ РЕЄСТРАЦІЇ", callback_data="reg_link")],
        [InlineKeyboardButton(text="✅ Я ЗАРЕЄСТРУВАВСЯ", callback_data="registered")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_start")],
        [InlineKeyboardButton(text="🆘 Допомога", callback_data="help")]
    ]
)

games_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        # Лейбл Краш-игры
        [InlineKeyboardButton(text="💥 Краш-игры 💥", callback_data="ignore")],
        [InlineKeyboardButton(text="💎 MINES 💎", web_app=WebAppInfo(url=f"{WEBAPP_BASE_URL}/minesexplorer-ukr")),
         InlineKeyboardButton(text="⚽ GOAL ⚽", web_app=WebAppInfo(url=f"{WEBAPP_BASE_URL}/goalrush-ukr"))],
        [InlineKeyboardButton(text="✈️ AVIATRIX ✈️", web_app=WebAppInfo(url=f"{WEBAPP_BASE_URL}/aviatrixflymod-ukr")),
         InlineKeyboardButton(text="🥅 PENALTY 🥅", web_app=WebAppInfo(url=f"{WEBAPP_BASE_URL}/penaltygame-ukr"))],

        # Лейбл Слот-игры
        [InlineKeyboardButton(text="🎰 Слот-игры 🎰", callback_data="ignore")],
        [InlineKeyboardButton(text="SWEET BONANZA", web_app=WebAppInfo(url=f"{WEBAPP_BASE_URL}/sweetbonanza-ukr")),
         InlineKeyboardButton(text="OLYMPUS", web_app=WebAppInfo(url=f"{WEBAPP_BASE_URL}/olympus-ukr"))],
        [InlineKeyboardButton(text="SUPREME HOT", web_app=WebAppInfo(url=f"{WEBAPP_BASE_URL}/supremehot-ukr")),
         InlineKeyboardButton(text="ROYAL COINS", web_app=WebAppInfo(url=f"{WEBAPP_BASE_URL}/royalcoins-ukr"))],

        # Кнопка помощи
        [InlineKeyboardButton(text="🆘 Допомога", callback_data="help")]
    ]
)


# --- Сообщение старта ---

async def send_start_text(bot: Bot, target, is_edit: bool = False):
    user_id = target.from_user.id

    if not await check_user_access_key(user_id, target):
        return
    text = (
        "👋 Вітаю!\n\n"
        "Ти потрапив у бот, який використовують для отримання доходу на онлайн-іграх за допомогою автоматизованої аналітики.\n\n"
        "Система створена так, щоб навіть новачок міг швидко розібратись і почати діяти без складнощів та досвіду.\n\n"
        "💰 Користувачі, які чітко дотримуються інструкцій, заробляють 100–300$ вже з першого дня, працюючи з телефону та з дому.\n\n"
        "❗️ Важливо:\n"
        "❌ нічого зламувати не потрібно\n"
        "❌ спеціальних знань не потрібно\n"
        "❌ все вже налаштовано за тебе\n\n"
        "Увесь процес розписаний покроково — 10–15 хвилин, і ти повністю розумієш, що робити далі.\n\n"
        "👇 Тисни кнопку нижче:"
    )
    if is_edit:
        await target.edit_text(text=text, reply_markup=how_it_works_keyboard)
    else:
        await bot.send_message(chat_id=target, text=text, reply_markup=how_it_works_keyboard)

    username = target.from_user.username or f"user_{target.from_user.id}"

    async with SessionLocal() as session:
        await save_step(session, target.from_user.id, "start", username)


async def send_access_granted_message(bot: Bot, message: Message, user_lang: str):
    user_id = message.from_user.id

    if not await check_user_access_key(user_id, message):
        return
    # user_lang оставляем как параметр, чтобы не ломать остальную логику
    keyboard = games_keyboard
    text = (
        "✅ ДОСТУП ОТРИМАНО ✅\n\n"
        "🔴 Інструкція:\n"
        "1️⃣ Виберіть гру нижче\n"
        "2️⃣ Відкрийте її на сайті\n"
        "3️⃣ Отримайте сигнал і повторіть його в грі ➕ 🐝"
    )
    await message.answer(text, reply_markup=keyboard)

    username = message.from_user.username or f"user_{message.from_user.id}"

    async with SessionLocal() as session:
        await save_step(session, message.from_user.id, "access_granted", username=username)

# --- Обработчик /start ---

async def check_user_access_key(user_id: int, bot_message: Message) -> bool:
    # if user_id in ALLOWED_USER_IDS:
    #     return True
    # """
    # Проверяет, есть ли у пользователя валидный ключ.
    # Если ключа нет — добавляет пользователя в awaiting_keys и отправляет сообщение.
    # Возвращает True, если ключ есть и пользователь может продолжать.
    # """
    # async with SessionLocal() as session:
    #     result = await session.execute(
    #         select(AccessKey).filter_by(telegram_id=user_id, entered=True)
    #     )
    #     access_key = result.scalar_one_or_none()
    #
    # if not access_key:
    #     awaiting_keys[user_id] = True
    #     await bot_message.answer(
    #         "🔑 Щоб отримати доступ, напишіть підтримці:\n"
    #         "👤 @supp_winbot\n\n"
    #         "Після отримання ключа введіть його тут, щоб почати роботу 🚀"
    #     )
    #     return False

    return True

@router.message(CommandStart())
async def start_handler(message: Message):
    user_id = message.from_user.id

    if not await check_user_access_key(user_id, message):
        return

    try:
        await message.answer(
            "👋 Вітаю!\n\n"
            "Ти потрапив у бот, який використовують для отримання доходу на онлайн-іграх за допомогою автоматизованої аналітики.\n\n"
            "Система створена так, щоб навіть новачок міг швидко розібратись і почати діяти без складнощів та досвіду.\n\n"
            "💰 Користувачі, які чітко дотримуються інструкцій, заробляють 100–300$ вже з першого дня, працюючи з телефону та з дому.\n\n"
            "❗️ Важливо:\n"
            "❌ нічого зламувати не потрібно\n"
            "❌ спеціальних знань не потрібно\n"
            "❌ все вже налаштовано за тебе\n\n"
            "Увесь процес розписаний покроково — 10–15 хвилин, і ти повністю розумієш, що робити далі.\n\n"
            "👇 Тисни кнопку нижче:",
            reply_markup=how_it_works_keyboard
        )

        parts = message.text.split(maxsplit=1)
        if len(parts) > 1:
            bot_tag = parts[1].strip()
            async with SessionLocal() as session:
                invite_result = await session.execute(
                    select(ReferralInvite).filter_by(bot_tag=bot_tag)
                )
                invite = invite_result.scalar_one_or_none()

                if invite:
                    await session.refresh(invite)
                    referral = await session.get(Referral, invite.referral_id)
                    if referral:
                        user_result = await session.execute(
                            select(User).filter_by(telegram_id=message.from_user.id)
                        )
                        user = user_result.scalar()

                        if not user:
                            user = User(
                                telegram_id=message.from_user.id,
                                username=message.from_user.username,
                                ref_tag=referral.tag,
                                bot_tag=bot_tag
                            )
                        else:
                            user.ref_tag = referral.tag
                            user.bot_tag = bot_tag

                        session.add(user)
                        await session.commit()

                        logging.info(
                            f"👤 Новый пользователь {message.from_user.id} пришёл по ссылке: /start={bot_tag}. "
                            f"Казино: {invite.casino_link}"
                        )
                    else:
                        logging.warning(f"⚠️ Invite найден, но Referral не найден")
                else:
                    logging.warning(
                        f"⚠️ Пользователь {message.from_user.id} пришёл с несуществующим bot_tag: {bot_tag}")

        username = message.from_user.username or f"user_{message.from_user.id}"

        async with SessionLocal() as session:
            await save_step(session, message.from_user.id, "start", username)

    except Exception as e:
        logging.error(f"❌ Ошибка в /start: {str(e)}")
        await message.answer("Произошла ошибка при старте.")

# --- Дальше по инструкции ---

@router.callback_query(F.data == "back_to_start")
async def back_to_start(callback: CallbackQuery):
    user_id = callback.from_user.id

    if not await check_user_access_key(user_id, callback.message):
        return
    await callback.answer()
    await send_start_text(bot=callback.bot, target=callback.message, is_edit=True)


@router.callback_query(F.data == "how_it_works")
async def how_it_works(callback: CallbackQuery):
    user_id = callback.from_user.id

    if not await check_user_access_key(user_id, callback.message):
        return
    await callback.answer()
    await callback.message.edit_text(
        "Основа системи — Telegram-бот з аналітичним модулем, який працює зі статистикою міні-ігор та повторюваними сценаріями.\n\n"
        "⚙️ Що саме він робить:\n"
        " • 📊 Аналізує серії виграшів і програшів\n"
        " • 🔄 Визначає повторювані патерни\n"
        " • ✅ Показує оптимальну послідовність дій\n\n"
        "<b>🛡 Ти не ризикуєш навмання і не приймаєш рішення «на удачу».</b>\n\n"
        "Твоє завдання просте: повторювати готову схему, яку дає бот, вже на реальній платформі.\n\n"
        "👇 Тисни кнопку нижче:",
        reply_markup=instruction_keyboard,
        parse_mode="HTML"
    )
    username = callback.from_user.username or f"user_{callback.from_user.id}"

    async with SessionLocal() as session:
        await save_step(session, callback.from_user.id, "how_it_works", username)

@router.callback_query(F.data == "get_instruction")
async def get_instruction(callback: CallbackQuery):
    user_id = callback.from_user.id

    if not await check_user_access_key(user_id, callback.message):
        return
    await callback.answer()

    await callback.message.answer(
        "1️⃣ Зареєструй акаунт на платформі, до якої підключений бот (посилання нижче).\n"
        "2️⃣ Після реєстрації скопіюй ID свого акаунта.\n"
        "3️⃣ Надішли ID сюди в бот.\n\n"
        "💡 Для чого це потрібно? Це необхідно, щоб система синхронізувалася саме з твоїм профілем.\n"
        "⚠️ Без ID бот не зможе активувати аналітику.\n"
        "🎥 Нижче я додав коротку відео-інструкцію, щоб тобі було простіше."
    )

    video_file_id = "BAACAgIAAxkBAAIW1mmZ70Pxs33ok-Hb7ottbnU1E_W-AAKqkAACV27RSHAEwXqQ2LrLOgQ"
    await callback.message.answer_video(video=video_file_id)

    await asyncio.sleep(15)

    await callback.message.answer(
        "💸 Твій перший прибуток вже зовсім поруч! Всього один крок відділяє тебе від старту. "
        "Реєструйся зараз, щоб заробити свої перші гроші вже сьогодні.",
        reply_markup=reg_inline_keyboard
    )
    username = callback.from_user.username or f"user_{callback.from_user.id}"

    async with SessionLocal() as session:
        await save_step(session, callback.from_user.id, "instruction", username)


# --- Регистрация пользователя через кнопку ---

@router.callback_query(F.data == "reg_link")
async def send_registration_link(callback: CallbackQuery):
    user_id = callback.from_user.id

    if not await check_user_access_key(user_id, callback.message):
        return
    await callback.answer()

    async with SessionLocal() as session:
        user_result = await session.execute(
             select(User).filter_by(telegram_id=callback.from_user.id)
         )
        user = user_result.scalar()

        referral_link = REGISTRATION_URL  # fallback
        if user and user.bot_tag:
            invite_result = await session.execute(
                select(ReferralInvite).filter_by(bot_tag=user.bot_tag)
            )
            invite = invite_result.scalar_one_or_none()
            if invite:
                referral_link = invite.casino_link
        logging.info(f"Generated registration link for user {callback.from_user.id}: {referral_link}")
        await callback.message.answer(f"Ось посилання для реєстрації: {referral_link}")
    username = callback.from_user.username or f"user_{callback.from_user.id}"

    async with SessionLocal() as session:
        await save_step(session, callback.from_user.id, "reg_link", username)

@router.callback_query(F.data == "help")
async def help_callback(callback: CallbackQuery):
    user_id = callback.from_user.id

    if not await check_user_access_key(user_id, callback.message):
        return
    await callback.answer()
    await callback.message.answer("Напишіть підтримці:\n@supp_winbot")


@router.callback_query(F.data == "registered")
async def registered(callback: CallbackQuery):
    user_id = callback.from_user.id

    if not await check_user_access_key(user_id, callback.message):
        return
    await callback.answer()
    awaiting_ids[callback.from_user.id] = True
    await callback.message.answer("🔢 Вкажи ID свого нового акаунта (тільки цифри)")

@router.callback_query(F.data == "continue_flow")
async def continue_flow(callback: CallbackQuery):
    user_id = callback.from_user.id

    if not await check_user_access_key(user_id, callback.message):
        return
    await callback.answer()

    async with SessionLocal() as session:
        result = await session.execute(
            select(UserProgress).filter_by(telegram_id=callback.from_user.id, bot_name="hackbotukr")
        )
        progress = result.scalar()

    if not progress:
        await send_start_text(callback.bot, callback.message, is_edit=True)
        return

    step = progress.last_step

    if step == "start":
        await send_start_text(callback.bot, callback.message, is_edit=True)

    elif step == "how_it_works":
        await how_it_works(callback)

    elif step == "instruction":
        await get_instruction(callback)

    elif step in ["entered_id", "access_granted"]:
        await send_access_granted_message(callback.bot, callback.message, "uk")

    else:
        await send_start_text(callback.bot, callback.message, is_edit=True)



# --- Проверка ID пользователя ---

@router.message()
async def process_user_message(message: Message):
    user_id = message.from_user.id

    # --- Если пользователь ожидает ключ ---
    if awaiting_keys.get(user_id):
        if not message.text:
            await message.answer("❌ Введи текст ключа.")
            return

        # Проверяем ключ в базе
        async with SessionLocal() as session:
            result = await session.execute(
                select(AccessKey).filter_by(key=message.text, entered=False)
            )
            access_key = result.scalar_one_or_none()

            if not access_key:
                await message.answer("❌ Невірний ключ. Спробуй ще раз.")
                return

            # Отмечаем ключ как введённый
            access_key.entered = True
            access_key.telegram_id = user_id
            access_key.username = message.from_user.username or f"user_{user_id}"
            await session.commit()

        # Убираем из awaiting_keys и даем доступ
        awaiting_keys.pop(user_id, None)
        await message.answer("✅ Ключ прийнято! Доступ надано.")
        await message.answer(
            "👋 Вітаю!\n\n"
            "Ти потрапив у бот, який використовують для отримання доходу на онлайн-іграх за допомогою автоматизованої аналітики.\n\n"
            "Система створена так, щоб навіть новачок міг швидко розібратись і почати діяти без складнощів та досвіду.\n\n"
            "💰 Користувачі, які чітко дотримуються інструкцій, заробляють 100–300$ вже з першого дня, працюючи з телефону та з дому.\n\n"
            "❗️ Важливо:\n"
            "❌ нічого зламувати не потрібно\n"
            "❌ спеціальних знань не потрібно\n"
            "❌ все вже налаштовано за тебе\n\n"
            "Увесь процес розписаний покроково — 10–15 хвилин, і ти повністю розумієш, що робити далі.\n\n"
            "👇 Тисни кнопку нижче:",
            reply_markup=how_it_works_keyboard
        )
        username = message.from_user.username or f"user_{message.from_user.id}"

        async with SessionLocal() as session:
            await save_step(session, message.from_user.id, "start", username)
        return

    # --- Если пользователь ожидает ID после регистрации ---
    if awaiting_ids.get(user_id):
        if not message.text.isdigit():
            await message.answer("❌ Введи тільки цифри.")
            return
        username = message.from_user.username or f"user_{user_id}"

        async with SessionLocal() as session:
            await save_step(session, user_id, "entered_id", username)

        await message.answer("🔍 Перевіряю ID у базі...")
        await send_access_granted_message(message.bot, message, "uk")
        awaiting_ids.pop(user_id, None)
        return

    # --- Если это видео или команда ---
    if message.video:
        logging.info(f"Received video from user {user_id}: {message.video.file_id}")
        return
    if message.text.startswith("/"):
        print(f"❓ Ненадіслана команда: {message.text}")
        await message.answer("❗ Невідома команда.")
        return

# --- Неизвестные колбэки ---

@router.callback_query()
async def catch_unhandled_callbacks(callback: CallbackQuery):
    user_id = callback.from_user.id

    if not await check_user_access_key(user_id, callback.message):
        return
    known_callbacks = [
        "help", "how_it_works", "get_instruction",
        "registered", "reg_link",
        "admin_stats", "admin_add", "admin_remove", "user_list",
        "admin_list", "add_ref_link", "remove_ref_link", "referral_stats", "ignore", "generate_key"
    ]

    if callback.data not in known_callbacks:
        await callback.answer()
        async with SessionLocal() as session:
            user_result = await session.execute(select(User).filter_by(telegram_id=callback.from_user.id))
            user = user_result.scalar()

        text = "Ви натиснули невідому кнопку!"
        await callback.message.answer(text)

