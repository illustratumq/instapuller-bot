from app.database.models import Account, Work
from app.keyboard.inline.base import *
from app.keyboard.inline.back import back_button
from app.keyboard.inline.accounts import account_cb

limit_cb = CallbackData('lm', 'account_id', 'action', 'val')
add_work_cb = CallbackData('wk', 'account_id', 'executor_id', 'action', 'mode')
mod_work_cb = CallbackData('wk', 'work_id', 'account_id', 'action')


def moderate_limit_kb(customer: Account):
    def button_cb(action: str, val: int):
        return limit_cb.new(account_id=customer.account_id, action=action, val=val)

    inline_keyboard = [
        [InlineKeyboardButton(str(num), callback_data=button_cb('set', num)) for num in (5, 10, 30, 40, 50)],
        [
            InlineKeyboardButton('➕ 1', callback_data=button_cb('plus', 1)),
            InlineKeyboardButton('➖ 1', callback_data=button_cb('minus', 1))
        ],
        [back_button(action='settings', account_id=customer.account_id)]
    ]
    return InlineKeyboardMarkup(row_width=2, inline_keyboard=inline_keyboard)


def confirm_moderate_kb(customer: Account, action: str):

    def button_cb(act: str):
        return account_cb.new(account_id=customer.account_id, type='posting', action=act)

    return InlineKeyboardMarkup(
        row_width=2,
        inline_keyboard=[
            [
                InlineKeyboardButton(Buttons.accounts.confirm, callback_data=button_cb(f'conf_{action}'))
            ],
            [back_button(action='settings', account_id=customer.account_id)]
        ]
    )


def construct_executors_kb(executors: list[Account], customer: Account):

    def button_cb(exc: Account, action: str):
        return add_work_cb.new(account_id=customer.account_id, executor_id=exc.account_id, action=action, mode='None')

    inline_keyboard = [
        [InlineKeyboardButton(executor.username, callback_data=button_cb(executor, 'select'))] for executor in executors
    ]
    inline_keyboard.append([back_button(action='posting', account_id=customer.account_id)])
    return InlineKeyboardMarkup(
        row_width=2,
        inline_keyboard=inline_keyboard
    )


def construct_work_mode_kb(executor: Account, customer: Account):

    def button_cb(mode: str):
        return add_work_cb.new(account_id=customer.account_id,
                               executor_id=executor.account_id, action='mode', mode=mode)

    inline_keyboard = [
        [InlineKeyboardButton(Buttons.accounts.work.all, callback_data=button_cb('all')),
         InlineKeyboardButton(Buttons.accounts.work.all_and_new, callback_data=button_cb('all_and_new'))],
        [InlineKeyboardButton(Buttons.accounts.work.only_new, callback_data=button_cb('only_new')),
         InlineKeyboardButton(Buttons.accounts.work.last_n, callback_data=button_cb('last_n'))],
        [back_button(action='work', account_id=customer.account_id)]
    ]
    return InlineKeyboardMarkup(row_width=2, inline_keyboard=inline_keyboard)


def confirm_add_work_kb(executor: Account, customer: Account, mode: str):

    def button_cb():
        return add_work_cb.new(account_id=customer.account_id,
                               executor_id=executor.account_id, action='confirm', mode=mode)

    return InlineKeyboardMarkup(
        row_width=1,
        inline_keyboard=[
            [
                InlineKeyboardButton(Buttons.accounts.confirm, callback_data=button_cb())
            ],
            [back_button(action='work', account_id=customer.account_id)]
        ]
    )


def delete_work_kb(works: list[Work], customer: Account):

    def button_cb(work: Work):
        return mod_work_cb.new(action='delete', work_id=work.work_id, account_id=customer.account_id)

    inline_keyboard = [
        [InlineKeyboardButton(str(num), callback_data=button_cb(work)) for work, num in zip(works, range(1, len(works)+1))],
        [back_button(action='posting', account_id=customer.account_id)]
    ]
    return InlineKeyboardMarkup(
        row_width=len(works),
        inline_keyboard=inline_keyboard
    )


def confirm_delete_work_kb(work: Work, customer: Account):
    def button_cb():
        return mod_work_cb.new(work_id=work.work_id, action='conf_delete', account_id=customer.account_id)

    return InlineKeyboardMarkup(
        row_width=1,
        inline_keyboard=[
            [InlineKeyboardButton(Buttons.accounts.confirm, callback_data=button_cb())],
            [back_button(action='posting', account_id=customer.account_id)]
        ]
    )


def edit_login_data_kb(customer: Account):

    def button_cb(action: str):
        return account_cb.new(account_id=customer.account_id, type='posting', action=action)

    return InlineKeyboardMarkup(
        row_width=2,
        inline_keyboard=[
            [
                InlineKeyboardButton(Buttons.accounts.edit_username, callback_data=button_cb('edit_username')),
                InlineKeyboardButton(Buttons.accounts.edit_password, callback_data=button_cb('edit_password'))
            ],
            [
                InlineKeyboardButton(Buttons.accounts.edit_auth_key, callback_data=button_cb('edit_auth'))
            ],
            [back_button(action='settings', account_id=customer.account_id)]
        ]
    )

