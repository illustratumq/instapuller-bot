from app.database.models import Account
from app.keyboard.inline.accounts import account_cb
from app.keyboard.inline.back import back_button
from app.keyboard.inline.base import *

admin_cb = CallbackData('adm', 'action', 'user_id', 'account_id')


def admin_kb():

    def button_cb(action: str):
        return dict(callback_data=admin_cb.new(action=action, user_id=0, account_id=0))

    inline_keyboard = [
        [
            InlineKeyboardButton(Buttons.admin.root, **button_cb('root')),
        ],
        [
            InlineKeyboardButton(Buttons.admin.technicals, **button_cb('tech')),
            InlineKeyboardButton(Buttons.admin.proxy, **button_cb('proxy'))
        ],
        [
            InlineKeyboardButton(Buttons.admin.download, **button_cb('download')),
            InlineKeyboardButton(Buttons.admin.subscribe, **button_cb('sub'))
        ],
        [
            back_button(text='Назад'),
            InlineKeyboardButton(Buttons.admin.update, **button_cb('update'))
        ]
    ]

    return InlineKeyboardMarkup(row_width=2, inline_keyboard=inline_keyboard)


def pre_root_accounts_kb(accounts: list[Account]):

    def button_cb(account):
        return dict(callback_data=admin_cb.new(account_id=account.account_id, user_id=account.user_id, action='run_root'))
    input_list = [InlineKeyboardButton(account.username, **button_cb(account)) for account in accounts]
    inline_keyboard = [input_list[i:i + 2] for i in range(0, len(input_list), 2)] + [[back_button(action='admin')]]
    return InlineKeyboardMarkup(row_width=2, inline_keyboard=inline_keyboard)
