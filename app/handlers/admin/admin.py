import os

import pandas as pd
from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import CallbackQuery, InputFile

from app.config import Config
from app.database.services.enums import AccountTypeEnum
from app.database.services.repos import AccountRepo, WorkRepo, UserRepo
from app.handlers.private.posting import posting_cmd
from app.keyboard import Buttons
from app.keyboard.inline.admin import pre_root_accounts_kb, admin_cb


async def pre_root_selecting(call: CallbackQuery, account_db: AccountRepo):
    await call.message.delete()
    accounts = await account_db.get_accounts_type(AccountTypeEnum.POSTING)
    text = (
        f'[Панель адміністратора| {Buttons.admin.root}]\n\n'
        f'Оберіть акаунт в який хочете перейти'
    )
    await call.message.answer(text, reply_markup=pre_root_accounts_kb(accounts))


async def run_root_cmd(call: CallbackQuery, callback_data: dict, config: Config,
                       account_db: AccountRepo, work_db: WorkRepo, state: FSMContext):
    user_id = int(callback_data['user_id'])
    await state.update_data(user_id=user_id)
    await posting_cmd(call, callback_data, config, account_db, work_db, state)


async def download_excel_cmd(call: CallbackQuery, account_db: AccountRepo):
    await call.answer()
    await call.bot.send_chat_action(call.from_user.id, 'upload_document')
    accounts = await account_db.get_accounts_type(AccountTypeEnum.POSTING)
    accounts += await account_db.get_accounts_type(AccountTypeEnum.TECHNICAL)
    data = {
        'account_id': [],
        'username': [],
        'password': [],
        'auth_key': [],
        'user_id': [],
        'status': [],
        'type': [],
        'subscript_days': []
    }
    for account in accounts:
        for key in data.keys():
            if key == 'type':
                value = account.get_account_type()
            elif key == 'status':
                value = account.get_status_string()
            else:
                value = account.__dict__[key]
            data[key].append(str(value))
    table_path = 'app/handlers/admin/Дані від акаунтів.xlsx'
    df = pd.DataFrame(data)
    with pd.ExcelWriter(table_path) as writer:
        df.to_excel(writer, sheet_name='Технічні акаунти', index=False)
    await call.message.answer_document(InputFile(table_path))
    os.remove(table_path)


def setup(dp: Dispatcher):
    dp.register_callback_query_handler(pre_root_selecting, admin_cb.filter(action='root'), state='*')
    dp.register_callback_query_handler(run_root_cmd, admin_cb.filter(action='run_root'), state='*')
    dp.register_callback_query_handler(download_excel_cmd, admin_cb.filter(action='download'), state='*')
