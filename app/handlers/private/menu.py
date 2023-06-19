from aiogram import Dispatcher
from aiogram.types import CallbackQuery

from app.database.services.repos import AccountRepo, AccountTypeEnum
from app.keyboard.inline.menu import select_accounts_kb, menu_cb


async def select_accounts(call: CallbackQuery, account_db: AccountRepo):
    user_accounts_parsing = await account_db.get_accounts_by_user(call.from_user.id, AccountTypeEnum.PARSING)
    user_accounts_posting = await account_db.get_accounts_by_user(call.from_user.id, AccountTypeEnum.POSTING)
    text = (
        '🗂 [Ваші акаунти]\n\n'
        f'📤 Для публікації: {len(user_accounts_posting)}\n'
        f'Акаунти на яких будуть публікуватися пости\n\n'
        f'📂 Для копіювання: {len(user_accounts_parsing)}\n'
        f'Акаунти з яких будуть копіюватися пости для публікації\n\n'
        f'🛠 Оберіть тип акаунта щоб перейти до налаштувань'
    )
    await call.message.edit_text(text, reply_markup=select_accounts_kb)

async def dev_cmd(call: CallbackQuery):
    await call.answer('Вже скоро 💫')


def setup(dp: Dispatcher):
    dp.register_callback_query_handler(select_accounts, menu_cb.filter(action='accounts'), state='*')
    dp.register_callback_query_handler(dev_cmd, menu_cb.filter(action='subscript'), state='*')
    dp.register_callback_query_handler(dev_cmd, menu_cb.filter(action='faq'), state='*')
