import logging
import re
import secrets
import string

from aiogram import types, Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import func
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from bot.admin_panel.admin_utils import (
    is_admin, remove_admin, list_admins, list_ref_links
)
from bot.database.db import SessionLocal
from bot.database.models import User, Admin, Referral, AccessKey
from bot.keyboards.admin_keyboards import admin_keyboard

router = Router()

# Вход в админ-панель
@router.message(Command("hiddenadmin"))
async def admin_start(message: types.Message):
    logging.info(f"[ADMIN PANEL] Попытка входа от {message.from_user.id}")

    #  Вставка отладки:
    print("Твой Telegram ID:", message.from_user.id)
    print("Результат проверки is_admin:", await is_admin(message.from_user.id))

    try:
        if await is_admin(message.from_user.id):
            await message.answer("✅ Добро пожаловать в админ-панель!", reply_markup=admin_keyboard)
            logging.info(f"[ADMIN PANEL] Админ {message.from_user.id} успешно вошёл в панель.")
        else:
            await message.answer("🚫 У вас нет прав администратора.")
            logging.warning(f"[ADMIN PANEL] Попытка входа без прав от {message.from_user.id}")
    except Exception as e:
        logging.error(f"[ADMIN PANEL] Ошибка входа: {str(e)}")
        await message.answer("❌ Произошла ошибка при входе в админ-панель.")

#проверка работоспособности команд
@router.message(Command("ping"))
async def test_ping(message: types.Message):
    await message.answer(
        f"✅ Бот работает. Твой Telegram ID: <code>{message.from_user.id}</code>",
        parse_mode="HTML"
    )


# Статистика пользователей и админов
@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    logging.info("[ADMIN PANEL] Получение статистики пользователей и админов")
    try:
        async with SessionLocal() as session:
            user_count = await session.scalar(select(func.count(User.id)))
            admin_count = await session.scalar(select(func.count(Admin.id)))
        await callback.message.answer(
            f"📊 <b>Статистика</b>\n\n"
            f"👥 Всего пользователей: <b>{user_count}</b>\n"
            f"🔑 Всего админов: <b>{admin_count}</b>",
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"[ADMIN PANEL] Ошибка получения статистики: {str(e)}")
        await callback.message.answer("❌ Ошибка получения статистики.")
    await callback.answer()

# Список пользователей
@router.callback_query(F.data == "user_list")
async def user_list(callback: CallbackQuery):
    logging.info("[ADMIN PANEL] Получение списка пользователей")
    try:
        async with SessionLocal() as session:
            result = await session.execute(select(User))
            users = result.scalars().all()
        if not users:
            await callback.message.answer("📭 Список пользователей пуст.")
            return await callback.answer()
        text = "\n".join([
            f"🆔 {user.telegram_id} - @{user.username or 'Без username'}"
            for user in users
        ])
        await callback.message.answer(f"📋 <b>Список пользователей:</b>\n\n{text}", parse_mode="HTML")
    except Exception as e:
        logging.error(f"[ADMIN PANEL] Ошибка получения списка пользователей: {str(e)}")
        await callback.message.answer("❌ Ошибка получения списка пользователей.")
    await callback.answer()

# Помощь по админ-панели
@router.message(Command("adminhelp"))
async def admin_help(message: types.Message):
    logging.info(f"[ADMIN PANEL] Запрос справки от {message.from_user.id}")
    if not await is_admin(message.from_user.id):
        return await message.answer("🚫 У вас нет прав администратора.")
    help_text = (
        "📖 <b>Справочник по админ-панели</b>\n\n"
        "🛠️ /hiddenadmin — Открыть админ-панель\n"
        "📊 Статистика — Количество пользователей и админов\n"
        "👥 Список пользователей — Посмотреть всех пользователей\n"
        "🗃️ Список админов — Посмотреть всех админов\n"
        "➕ Добавление и удаление админов — Через админ-панель\n"
        "🔗 Список реф. ссылок — Просмотр и управление реф-ссылками\n"
        "👷 Управление вебмастерами — Добавление, ссылки, переназначение\n"
        "📈 Статистика вебмастеров — Количество созданных тегов и ссылок\n"
        "❌ Удаление вебмастеров и админов — через админ-панель"
    )
    await message.answer(help_text, parse_mode="HTML")

# Список реферальных ссылок (не привязанных к вебмастерам)
@router.callback_query(F.data == "referral_list")
async def show_referral_list(callback: CallbackQuery):
    logging.info("[ADMIN PANEL] Запрошен список реферальных ссылок")
    try:
        refs = await list_ref_links()
        if refs:
            text = "\n".join([f"🔗 {r.link}" for r in refs])
        else:
            text = "📭 Список реферальных ссылок пуст."
        await callback.message.answer(text)
    except Exception as e:
        logging.error(f"[ADMIN PANEL] Ошибка при получении списка реф-ссылок: {str(e)}")
        await callback.message.answer("❌ Ошибка получения списка реферальных ссылок.")
    await callback.answer()

# ❌ Удаление реферальной ссылки через выбор
@router.callback_query(F.data == "remove_ref_link")
async def remove_referral_list(callback: CallbackQuery):
    logging.info("[ADMIN PANEL] Запрошено удаление реф-ссылок")
    try:
        refs = await list_ref_links()
        if not refs:
            await callback.message.answer("📭 Список реферальных ссылок пуст.")
            return await callback.answer()

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Удалить: {ref.link}", callback_data=f"delete_link:{ref.id}")]
            for ref in refs
        ])
        await callback.message.answer("Выберите ссылку для удаления:", reply_markup=kb)
    except Exception as e:
        logging.error(f"[ADMIN PANEL] Ошибка получения реф-ссылок для удаления: {str(e)}")
        await callback.message.answer("❌ Ошибка получения списка ссылок.")
    await callback.answer()

@router.callback_query(F.data.startswith("delete_link:"))
async def delete_referral(callback: CallbackQuery):
    ref_id = int(callback.data.split(":")[1])
    logging.info(f"[ADMIN PANEL] Удаление реферальной ссылки ID {ref_id}")
    try:
        async with SessionLocal() as session:
            referral = await session.get(Referral, ref_id)
            if referral:
                link = referral.link
                await session.delete(referral)
                await session.commit()
                await callback.message.answer(f"✅ Ссылка {link} успешно удалена.")
            else:
                await callback.message.answer("❌ Ссылка не найдена.")
    except Exception as e:
        logging.error(f"[ADMIN PANEL] Ошибка удаления ссылки: {str(e)}")
        await callback.message.answer("❌ Не удалось удалить ссылку.")
    await callback.answer()

# Вывод вебмастеров по админам
@router.callback_query(F.data == "admin_list")
async def show_admin_list(callback: CallbackQuery):
    admins = await list_admins()

    if not admins:
        await callback.message.answer("❗️ Список админов пуст.")
        return await callback.answer()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"@{admin.username}" if admin.username else f"ID {admin.telegram_id}",
            callback_data=f"admin_wm_list:{admin.telegram_id}"
        )]
        for admin in admins
    ])
    await callback.message.answer("Выберите администратора для просмотра его вебмастеров:", reply_markup=kb)
    await callback.answer()

def generate_random_key(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

@router.callback_query(F.data == "generate_key")
async def generate_key(callback: CallbackQuery):
    telegram_id = callback.from_user.id

    # generate key
    key = generate_random_key()

    # save to DB
    async with SessionLocal() as session:
        session.add(AccessKey(key=key, entered=False))
        await session.commit()

    # answer user
    await callback.message.answer(
        f"🔑 Ваш новый ключ:\n\n<code>{key}</code>",
        parse_mode="HTML"
    )

    await callback.answer()

@router.callback_query(F.data.startswith("admin_wm_list:"))
async def show_admin_webmasters(callback: CallbackQuery):
    admin_id = int(callback.data.split(":")[1])

    async with SessionLocal() as session:
        result = await session.execute(
            select(Referral).filter_by(admin_id=admin_id).options(selectinload(Referral.links))
        )
        referrals = result.scalars().all()

    if not referrals:
        await callback.message.answer("📭 У этого администратора нет вебмастеров.")
        return await callback.answer()

    text_blocks = []
    for ref in referrals:
        main_link = next((l for l in ref.links if l.is_main), None)
        other_links = [l for l in ref.links if not l.is_main]

        block = f"🔹 Вебмастер <b>{ref.tag}</b>\n"
        if main_link:
            block += f"⭐ Основная: <code>{main_link.link}</code>\n"
        if other_links:
            block += "📎 Доп. ссылки:\n" + "\n".join(
                [f"🔸 <code>{l.link}</code>" for l in other_links]
            )
        block += "\n<code>────────────</code>"
        text_blocks.append(block)

    await callback.message.answer("\n\n".join(text_blocks), parse_mode="HTML")
    await callback.answer()

# Удаление администратора
@router.callback_query(F.data == "admin_remove")
async def choose_admin_to_remove(callback: CallbackQuery, state: FSMContext):
    admins = await list_admins()

    if not admins:
        await callback.message.answer("⚠️ Администраторов нет.")
        return await callback.answer()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"Удалить: {admin.telegram_id} - @{admin.username}",
            callback_data=f"remove_admin:{admin.telegram_id}"
        )]
        for admin in admins
    ])
    await callback.message.answer("Выберите администратора для удаления:", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("remove_admin:"))
async def confirm_admin_removal(callback: CallbackQuery, state: FSMContext):
    admin_id = int(callback.data.split(":")[1])
    await state.update_data(removing_admin_id=admin_id)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_admin_removal")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_admin_removal")]
    ])
    await callback.message.answer(
        f"Вы уверены, что хотите удалить администратора с ID {admin_id}?",
        reply_markup=kb
    )
    await callback.answer()

@router.callback_query(F.data == "confirm_admin_removal")
async def remove_admin_confirmed(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    admin_id = data.get("removing_admin_id")

    try:
        await remove_admin(admin_id)
        await callback.message.answer(f"✅ Администратор с ID {admin_id} успешно удалён.")
    except Exception as e:
        await callback.message.answer(f"❌ Не удалось удалить администратора: {str(e)}")

    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "cancel_admin_removal")
async def cancel_admin_removal(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("❌ Удаление администратора отменено.")
    await state.clear()
    await callback.answer()

# Статистика вебмастеров
@router.callback_query(F.data == "webmaster_stats")
async def webmaster_stats(callback: CallbackQuery):
    logging.info("[ADMIN PANEL] Получение статистики вебмастеров")

    async with SessionLocal() as session:
        result = await session.execute(
            select(Referral).options(selectinload(Referral.links))
        )
        referrals = result.scalars().all()

    total_webmasters = len(referrals)
    total_links = sum(len(ref.links) for ref in referrals)

    await callback.message.answer(
        f"📈 <b>Статистика вебмастеров</b>\n\n"
        f"👷 Всего вебмастеров (тегов): <b>{total_webmasters}</b>\n"
        f"🔗 Всего ссылок (основных и дополнительных): <b>{total_links}</b>",
        parse_mode="HTML"
    )
    await callback.answer()

# Открытие меню вебмастеров
@router.callback_query(F.data == "webmaster_menu")
async def open_webmaster_menu(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Список вебмастеров", callback_data="webmaster_links")],
        [InlineKeyboardButton(text="➕ Добавить вебмастера", callback_data="add_webmaster")],
        [InlineKeyboardButton(text="✏️ Изменить ссылку", callback_data="edit_webmaster_link")],
        [InlineKeyboardButton(text="🔁 Переназначить", callback_data="reassign_webmaster")],
        [InlineKeyboardButton(text="📈 Статистика", callback_data="webmaster_stats")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back_to_main")]
    ])
    await callback.message.edit_text("Выберите действие с вебмастерами:", reply_markup=kb)
    await callback.answer()


# Возврат в главное меню
@router.callback_query(F.data == "admin_back_to_main")
async def back_to_admin_main(callback: CallbackQuery):
    from bot.keyboards.admin_keyboards import admin_keyboard
    await callback.message.edit_text("✅ Главное меню администратора:", reply_markup=admin_keyboard)
    await callback.answer()

# проверка корректности ссылки
def is_valid_http_url(url: str) -> bool:
    return re.match(r"^https?://", url.strip()) is not None
