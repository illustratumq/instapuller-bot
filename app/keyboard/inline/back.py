from app.keyboard.inline.base import *

back_cb = CallbackData('bk', 'action', 'account_id')


def back_button(text: str = Buttons.menu.back, action: str = 'start', account_id: int = -1):
    return InlineKeyboardButton(text, callback_data=back_cb.new(action=action, account_id=account_id))


def back_keyboard(text: str = Buttons.menu.back, action: str = 'start', account_id: int = -1):
    return InlineKeyboardMarkup(row_width=1, inline_keyboard=[[back_button(text, action, account_id)]])
