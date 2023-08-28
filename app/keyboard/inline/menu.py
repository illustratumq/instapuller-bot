from app.config import Config
from app.keyboard.inline.back import back_button
from app.keyboard.inline.base import *

menu_cb = CallbackData('menu', 'action')
config = Config.from_env()


def help_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(Buttons.menu.help, url='https://t.me/instapuller_support')]])

def menu_kb(admin: bool = False):
    inline_keyboard = [
        [
            InlineKeyboardButton(Buttons.menu.my_accounts, callback_data=menu_cb.new(action='accounts')),
            InlineKeyboardButton(Buttons.menu.add_account, callback_data=menu_cb.new(action='add_account'))
        ],
        [
            InlineKeyboardButton(Buttons.menu.subscription, callback_data=menu_cb.new(action='subscript')),
            InlineKeyboardButton(Buttons.menu.help, url='https://t.me/instapuller_support')
        ],
        [
            InlineKeyboardButton(Buttons.menu.FAQ, callback_data=menu_cb.new(action='faq'))
        ]
    ]
    if admin:
        del inline_keyboard[-1]
        inline_keyboard += [
            [InlineKeyboardButton(Buttons.menu.admin, callback_data=menu_cb.new(action='admin'))],
            [InlineKeyboardButton(Buttons.admin.web, url=f'http://{config.misc.server_host_ip}:8000/admin')]
        ]
    return InlineKeyboardMarkup(
        row_width=2,
        inline_keyboard=inline_keyboard
    )


select_accounts_kb = InlineKeyboardMarkup(
    row_width=2,
    inline_keyboard=[
        [InlineKeyboardButton(Buttons.menu.add_account, callback_data=menu_cb.new(action='add_account'))],
        [
            InlineKeyboardButton(Buttons.menu.to_posting, callback_data=menu_cb.new(action='posting')),
            InlineKeyboardButton(Buttons.menu.to_parsing, callback_data=menu_cb.new(action='parsing'))
        ],
        [back_button()]
    ]
)