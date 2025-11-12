from aiogram import Bot, Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, WebAppInfo
from aiogram.filters import CommandStart
from sqlalchemy.future import select

from bot.database.db import SessionLocal
from bot.database.models import User, Referral, ReferralInvite
from bot.config import WEBAPP_BASE_URL, REGISTRATION_URL
import logging

router = Router()
awaiting_ids = {}



# --- Клавиатуры ---

lang_inline_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Русский", callback_data="lang_ru")],
        [InlineKeyboardButton(text="English", callback_data="lang_en")]
    ]
)

reg_inline_keyboard_ru = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🔗 ССЫЛКА ДЛЯ РЕГИСТРАЦИИ", callback_data="reg_link_ru")],
        [InlineKeyboardButton(text="✅ ЗАРЕГИСТРИРОВАЛСЯ", callback_data="registered_ru")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_lang")]
    ]
)

reg_inline_keyboard_en = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🔗 REGISTER LINK", callback_data="reg_link_en")],
        [InlineKeyboardButton(text="✅ I HAVE REGISTERED", callback_data="registered_en")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="back_to_lang")]
    ]
)

games_keyboard_ru = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="💎 MINES 💎", web_app=WebAppInfo(url=f"{WEBAPP_BASE_URL}/minesexplorer/")),
            InlineKeyboardButton(text="⚽ GOAL ⚽", web_app=WebAppInfo(url=f"{WEBAPP_BASE_URL}/goalrush/"))
        ],
        [
            InlineKeyboardButton(text="✈️ AVIATRIX ✈️", web_app=WebAppInfo(url=f"{WEBAPP_BASE_URL}/aviatrixflymod/")),
            InlineKeyboardButton(text="🥅 PENALTY 🥅", web_app=WebAppInfo(url=f"{WEBAPP_BASE_URL}/penaltygame/"))
        ],
    ]
)

games_keyboard_en = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="💎 MINES 💎", web_app=WebAppInfo(url=f"{WEBAPP_BASE_URL}/minesexplorer-en/")),
            InlineKeyboardButton(text="⚽ GOAL ⚽", web_app=WebAppInfo(url=f"{WEBAPP_BASE_URL}/goalrush-en/"))
        ],
        [
            InlineKeyboardButton(text="✈️ AVIATRIX ✈️", web_app=WebAppInfo(url=f"{WEBAPP_BASE_URL}/aviatrixflymod-en/")),
            InlineKeyboardButton(text="🥅 Penalty Shoot-out 🥅", web_app=WebAppInfo(url=f"{WEBAPP_BASE_URL}/penaltygame-en/"))
        ],
    ]
)

# Сообщение старта 

async def send_start_text(bot: Bot, target, is_edit: bool = False):
    text = (
        "Добро пожаловать в сигнальный бот CasinoHack🤖\n"
        "Welcome to the CasinoHack signal bot🤖\n\n"
        "Данный бот создан и обучен на кластере нейросети ChatGPT-v4.0🧠\n"
        "This bot is created and trained on a ChatGPT-v4.0 neural cluster🧠\n\n"
        "Продолжая, Вы соглашаетесь, что вся информация бесплатна и предоставлена исключительно в ознакомительных целях.\n"
        "By continuing, you agree that all information is for educational purposes only.\n\n"
        "Выберите язык / Choose a language 👇"
    )
    if is_edit:
        await target.edit_text(text=text, reply_markup=lang_inline_keyboard)
    else:
        await bot.send_message(chat_id=target, text=text, reply_markup=lang_inline_keyboard)

async def send_access_granted_message(bot: Bot, message: Message, user_lang: str):
    keyboard = games_keyboard_en if user_lang == "en" else games_keyboard_ru
    text = (
        "✅ ACCESS GRANTED ✅\n\n"
        "🔴 Instructions:\n"
        "1️⃣ Select a game below\n"
        "2️⃣ Open it on the site\n"
        "3️⃣ Get the signal and follow it in the game ➕ 🐝"
    ) if user_lang == "en" else (
        "✅ ДОСТУП ОТКРЫТ ✅\n\n"
        "🔴 Инструкция:\n"
        "1️⃣ Выберите игру ниже\n"
        "2️⃣ Откройте её на сайте\n"
        "3️⃣ Получите сигнал и повторите его в игре ➕ 🐝"
    )
    await message.answer(text, reply_markup=keyboard)

# Обработчик /start 

@router.message(CommandStart())
async def start_handler(message: Message):
    try:
        await message.answer(
            "Добро пожаловать в сигнальный бот CasinoHack🤖\n"
            "Welcome to the CasinoHack signal bot🤖\n\n"
            "Продолжая, Вы соглашаетесь, что вся информация бесплатна и предоставлена исключительно в ознакомительных целях.\n"
            "By continuing, you agree that all information is for educational purposes only.\n\n"
            "Выберите язык / Choose a language 👇",
            reply_markup=lang_inline_keyboard
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
                    logging.warning(f"⚠️ Пользователь {message.from_user.id} пришёл с несуществующим bot_tag: {bot_tag}")

    except Exception as e:
        logging.error(f"❌ Ошибка в /start: {str(e)}")
        await message.answer("Произошла ошибка при старте.")


# Регистрация пользователя через кнопку 
@router.callback_query(F.data.in_(["reg_link_ru", "reg_link_en"]))
async def send_registration_link(callback: CallbackQuery):
    await callback.answer()
    lang = "ru" if callback.data == "reg_link_ru" else "en"

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

        text = (
            f"Вот ссылка для регистрации: {referral_link}"
            if lang == "ru"
            else f"Here is the registration link: {referral_link}"
        )
        await callback.message.answer(text)

#  Подтверждение регистрации 

@router.callback_query(F.data == "registered_ru")
async def registered_ru(callback: CallbackQuery):
    await callback.answer()
    awaiting_ids[callback.from_user.id] = {"awaiting": True, "lang": "ru"}
    await callback.message.answer("Введите ID нового аккаунта (только цифры)")

@router.callback_query(F.data == "registered_en")
async def registered_en(callback: CallbackQuery):
    await callback.answer()
    awaiting_ids[callback.from_user.id] = {"awaiting": True, "lang": "en"}
    await callback.message.answer("Enter the ID of your new account (numbers only)")


#  Выбор языка 

@router.callback_query(F.data == "lang_ru")
async def lang_ru_selected(callback: CallbackQuery):
    await callback.answer()
    async with SessionLocal() as session:
        user_result = await session.execute(select(User).filter_by(telegram_id=callback.from_user.id))
        user = user_result.scalar()

        if user:
            user.language = "ru"
            await session.commit()

    await callback.message.edit_text(
        "Бот работает только с новыми аккаунтами, созданными по ссылке.\n\n"
        "Чтобы получить доступ, зарегистрируйтесь по ссылке и отправьте ID нового аккаунта (только цифры).\n\n"
        "Ссылка для регистрации 👇",
        reply_markup=reg_inline_keyboard_ru
    )

@router.callback_query(F.data == "lang_en")
async def lang_en_selected(callback: CallbackQuery):
    await callback.answer()
    async with SessionLocal() as session:
        user_result = await session.execute(select(User).filter_by(telegram_id=callback.from_user.id))
        user = user_result.scalar()

        if user:
            user.language = "en"
            await session.commit()

    await callback.message.edit_text(
        "This bot works only with newly created accounts registered via the link below.\n\n"
        "Please register a new account and send your ID (numbers only) to the bot.\n\n"
        "Registration link 👇",
        reply_markup=reg_inline_keyboard_en
    )


# Назад в выбор языка

@router.callback_query(F.data == "back_to_lang")
async def back_to_language(callback: CallbackQuery):
    await callback.answer()
    await send_start_text(bot=callback.bot, target=callback.message, is_edit=True)


# Проверка ID пользователя

@router.message()
async def process_user_message(message: Message):
    if message.text.startswith("/"):
        # Обработка неизвестной команды
        print(f"❓ Необработанная команда: {message.text}")
        await message.answer("❗ Неизвестная команда.")
        return

    user_data = awaiting_ids.get(message.from_user.id)
    if not user_data or not user_data.get("awaiting"):
        return

    lang = user_data.get("lang", "ru")
    bot = message.bot

    if not message.text.isdigit():
        await message.answer("❌ Error: Please enter numbers only." if lang == "en" else "❌ Ошибка: введите только цифры.")
        return

    user_id = message.text.strip()
    if not (
        (len(user_id) == 9 and user_id.startswith("23")) or
        (len(user_id) == 7 and user_id.startswith("4")) or
        (len(user_id) == 9 and user_id.startswith("3"))
    ):
        await message.answer("❌ Error: Please enter a valid ID." if lang == "en" else "❌ Ошибка: введите корректный ID.")
        return

    await message.answer("🔍 Checking ID in the database..." if lang == "en" else "🔍 Проверяю ID в базе...")
    await send_access_granted_message(bot, message, lang)
    awaiting_ids.pop(message.from_user.id, None)



#  Неизвестные колбэки 

@router.callback_query()
async def catch_unhandled_callbacks(callback: CallbackQuery):
    known_callbacks = [
        "registered_ru", "registered_en", "reg_link_ru", "reg_link_en",
        "lang_ru", "lang_en", "back_to_lang",
        "admin_stats", "admin_add", "admin_remove", "user_list",
        "admin_list", "add_ref_link", "remove_ref_link", "referral_stats"
    ]

    if callback.data not in known_callbacks:
        await callback.answer()

        async with SessionLocal() as session:
            user_result = await session.execute(select(User).filter_by(telegram_id=callback.from_user.id))
            user = user_result.scalar()

        lang = user.language if user else "ru"
        text = "You clicked an unknown button!" if lang == "en" else "Вы нажали неизвестную кнопку!"
        await callback.message.answer(text)
