from dataclasses import dataclass

from app.database.models import Account, User
from app.database.services.enums import AccountStatusEnum
from app.keyboard.inline.back import back_button
from app.keyboard.inline.base import *
from app.keyboard.inline.menu import menu_cb


account_cb = CallbackData('ac', 'action', 'account_id', 'type')


@dataclass
class Switch:
    Next: str = 'next'
    Prev: str = 'prev'


def switch(ids: list[int], account_id: int, action: str):
    if action == Switch.Next:
        return ids[(ids.index(account_id) + 1) % len(ids)]
    elif action == Switch.Prev:
        return ids[(ids.index(account_id) - 1) % len(ids)]


def customers_kb(customers: list[Account], account: Account, dev: bool = False, del_work: bool = False):
    ids = [customer.account_id for customer in customers]
    next_btn_cb = account_cb.new(account_id=switch(ids, account.account_id, Switch.Next), type='posting', action='pag')
    prev_btn_cb = account_cb.new(account_id=switch(ids, account.account_id, Switch.Prev), type='posting', action='pag')

    def button_cb(action: str):
        return account_cb.new(account_id=account.account_id, type='posting', action=action)

    inline_keyboard = [
        [
            InlineKeyboardButton(Buttons.accounts.add_work, callback_data=button_cb('add_work')),
        ],
        [
            InlineKeyboardButton(Buttons.accounts.settings, callback_data=button_cb('settings')),
            InlineKeyboardButton(Buttons.accounts.statistic, callback_data=button_cb('statistic'))
        ]
    ]
    if account.status == AccountStatusEnum.BANNED:
        inline_keyboard = [
            [InlineKeyboardButton(Buttons.accounts.login_data, callback_data=button_cb('login_data'))],
            [InlineKeyboardButton(Buttons.accounts.refresh_status, callback_data=button_cb('conf_resume'))], []
        ]
    if account.status == AccountStatusEnum.UNPAID:
        inline_keyboard = [
            [InlineKeyboardButton(Buttons.accounts.pay, callback_data=button_cb('pay'))],
            [InlineKeyboardButton(Buttons.accounts.delete, callback_data=button_cb('delete'))]
        ]
    account_in_bad_status = account.status in (AccountStatusEnum.UNPAID, AccountStatusEnum.BANNED)
    if dev:
        inline_keyboard[-1] = [
            InlineKeyboardButton(Buttons.accounts.settings[0], callback_data=button_cb('settings')),
            InlineKeyboardButton(Buttons.accounts.statistic[0], callback_data=button_cb('statistic')),
            InlineKeyboardButton(Buttons.accounts.developer[0], callback_data=button_cb('dev'))
        ]
    if del_work and not account_in_bad_status:
        inline_keyboard[0].append(InlineKeyboardButton(Buttons.accounts.del_work, callback_data=button_cb('del_work')))

    navigate_keyboard = [
        [
            InlineKeyboardButton('⬅', callback_data=prev_btn_cb),
            InlineKeyboardButton(Buttons.accounts.back, callback_data=menu_cb.new(action='accounts')),
            InlineKeyboardButton('➡', callback_data=next_btn_cb)
        ]
    ]
    return InlineKeyboardMarkup(
        row_width=3,
        inline_keyboard=inline_keyboard+navigate_keyboard
    )


def customer_settings_cb(account: Account):

    def button_cb(action: str):
        return account_cb.new(account_id=account.account_id, type='posting', action=action)

    if account.status == AccountStatusEnum.PAUSE:
        action_btn = InlineKeyboardButton(Buttons.accounts.resume, callback_data=button_cb('resume'))
    else:
        action_btn = InlineKeyboardButton(Buttons.accounts.pause, callback_data=button_cb('pause'))

    inline_keyboard = [
        [
            InlineKeyboardButton(Buttons.accounts.limit, callback_data=button_cb('limit')),
            InlineKeyboardButton(Buttons.accounts.login_data, callback_data=button_cb('login_data'))
        ],
        [
            action_btn,
            InlineKeyboardButton(Buttons.accounts.delete, callback_data=button_cb('delete'))
        ],
        [back_button(action='posting', account_id=account.account_id)]
    ]
    return InlineKeyboardMarkup(
        row_width=2,
        inline_keyboard=inline_keyboard
    )


def executor_kb(executors: list[Account], account: Account):
    executors.sort(key=lambda acc: acc.created_at)
    ids = [executor.account_id for executor in executors]
    next_btn_cb = account_cb.new(account_id=switch(ids, account.account_id, Switch.Next), type='parsing', action='pag')
    prev_btn_cb = account_cb.new(account_id=switch(ids, account.account_id, Switch.Prev), type='parsing', action='pag')

    def button_cb(action: str):
        return account_cb.new(account_id=account.account_id, type='parsing', action=action)

    inline_keyboard = [
        [
            InlineKeyboardButton(Buttons.menu.add_account, callback_data=menu_cb.new(action=f'add_parsing')),
            InlineKeyboardButton(Buttons.accounts.delete, callback_data=button_cb('delete'))
        ]
    ]
    navigate_keyboard = [
        [
            InlineKeyboardButton('⬅', callback_data=prev_btn_cb),
            InlineKeyboardButton(Buttons.accounts.back, callback_data=menu_cb.new(action='accounts')),
            InlineKeyboardButton('➡', callback_data=next_btn_cb)
        ]
    ]
    return InlineKeyboardMarkup(
        row_width=3,
        inline_keyboard=inline_keyboard + navigate_keyboard
    )


def customer_add_kb(url: str, help: bool = False):
    inline_keyboard = [
        [
            InlineKeyboardButton(Buttons.accounts.auth_help, url=url)
        ],
        [
            back_button('Відмінити'),
            InlineKeyboardButton(Buttons.accounts.skip, callback_data=menu_cb.new(action='skip_2fa'))
        ]
    ]
    if help:
        inline_keyboard[0].append(InlineKeyboardButton(Buttons.menu.help, url='https://t.me/instapuller_support'))
    return InlineKeyboardMarkup(
        row_width=2, inline_keyboard=inline_keyboard

    )


def add_account_kb(account_type: str):
    """
    :param account_type: "parsing/posting"
    """
    add_btn_cb = menu_cb.new(action=f'add_{account_type}')
    return InlineKeyboardMarkup(
        row_width=1,
        inline_keyboard=[
            [
                InlineKeyboardButton(Buttons.menu.add_account, callback_data=add_btn_cb)
            ],
            [back_button(action='accounts')]
        ]
    )


add_accounts_kb = InlineKeyboardMarkup(
    row_width=2,
    inline_keyboard=[
        [
            InlineKeyboardButton(Buttons.menu.to_posting, callback_data=menu_cb.new(action='add_posting')),
            InlineKeyboardButton(Buttons.menu.to_parsing, callback_data=menu_cb.new(action='add_parsing'))
        ],
        [back_button(action='accounts')]
    ]
)


def add_account_confirm_kb(account_type: str, back_action: str = 'accounts', **kwargs):
    conf_btn_cb = menu_cb.new(action=f'conf_add_{account_type}')
    return InlineKeyboardMarkup(
        row_width=1,
        inline_keyboard=[
            [
                InlineKeyboardButton(Buttons.accounts.confirm, callback_data=conf_btn_cb)
            ],
            [back_button('Відмінити', back_action, **kwargs)]
        ]
    )


def update_statistic_kb(customer_id: int, detail: bool = False):

    def button_cb(action: str):
        return account_cb.new(account_id=customer_id, type='posting', action=action)

    inline_keyboard = [
        [back_button(action='posting', account_id=customer_id),
         InlineKeyboardButton(Buttons.accounts.update, callback_data=button_cb('update_statistic'))]
    ]
    if detail:
        inline_keyboard.insert(0, [InlineKeyboardButton(Buttons.accounts.detail_statistic,
                                                        callback_data=button_cb('detail_statistic'))])

    return InlineKeyboardMarkup(
        row_width=1, inline_keyboard=inline_keyboard
    )


def developer_statistic_kb(customer: Account, user: User, detail: bool = False):

    def button_cb(action: str):
        return account_cb.new(account_id=customer.account_id, type='posting', action=action)

    inline_keyboard = [
        [InlineKeyboardButton(f'💬 Зв\'язатись з {user.full_name}', url=f"tg://user?id={customer.user_id}")],
        [back_button(action='posting', account_id=customer.account_id)]
    ]
    if detail:
        inline_keyboard.insert(0, [InlineKeyboardButton(Buttons.accounts.detail_statistic,
                                                        callback_data=button_cb('detail_statistic'))])
    return InlineKeyboardMarkup(
        row_width=1, inline_keyboard=inline_keyboard
    )