from aiogram import Dispatcher
from aiogram.types import CallbackQuery

from app.database.models import Account
from app.database.services.enums import AccountTypeEnum
from app.database.services.repos import AccountRepo, WorkRepo
from app.handlers.private.add import add_account_parsing
from app.handlers.private.decorator import construct_accounts_list, construct_work_mode, construct_work_status
from app.keyboard.inline.accounts import executor_kb, account_cb
from app.keyboard.inline.menu import menu_cb


async def parsing_cmd(call: CallbackQuery, callback_data: dict, account_db: AccountRepo, work_db: WorkRepo):
    user_id = callback_data['user_id'] if 'user_id' in callback_data.keys() else call.from_user.id
    executors = await account_db.get_accounts_by_user(user_id, AccountTypeEnum.PARSING)
    if not executors:
        return await add_account_parsing(call)
    executors.sort(key=lambda acc: acc.created_at)
    executor_id = int(callback_data['account_id']) if callback_data['action'] == 'pag' else executors[0].account_id
    executor = await account_db.get_account(executor_id)
    text = (
        f'📂 [Ваші акаунти | Для копіювання]\n\n'
        f'{construct_accounts_list(executors, executor)}\n'
        f'<b>🆔 Акаунт</b>: {executor.account_id}\n\n'
        f'{await construct_executor_works(executor, work_db, account_db)}'
    )
    await call.message.edit_text(text, reply_markup=executor_kb(executors, executor))


def setup(dp: Dispatcher):
    dp.register_callback_query_handler(parsing_cmd, menu_cb.filter(action='parsing'), state='*')
    dp.register_callback_query_handler(parsing_cmd, account_cb.filter(type='parsing'), state='*')


async def construct_executor_works(account: Account, work_db: WorkRepo, account_db: AccountRepo) -> str:
    works = await work_db.get_work_executor(account.account_id)
    text = f'🔗 Завдання пов\'язані з цим акаунтом:'
    if not works:
        return text + ' Не знайдено'
    else:
        text += '\n'
    for work, num in zip(works, range(1, len(works) + 1)):
        customer = await account_db.get_account(work.customer_id)
        text += f'   {num}. Для {customer.username} ({construct_work_mode(work)} {construct_work_status(work)})\n'
    return text
