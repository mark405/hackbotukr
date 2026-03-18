from aiogram.fsm.state import State, StatesGroup

class AdminStates(StatesGroup):
    awaiting_add_id = State()
    awaiting_remove_id = State()
    awaiting_ref_link = State()
    awaiting_webmaster_id = State()  
    confirming_webmaster_id = State()  
    awaiting_webmaster_link = State()  
    confirming_webmaster_link = State()  
    awaiting_new_referral_link = State()
    awaiting_webmaster_reassign = State()
    awaiting_new_admin_id = State()
    awaiting_new_link_for_webmaster = State()

    # Добавлено для "бот + казино"
    awaiting_bot_tag = State()
    awaiting_casino_link = State()
    awaiting_video = State()
    awaiting_edit_casino_link = State()
