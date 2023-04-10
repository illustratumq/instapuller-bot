from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import CallbackQuery

from app.config import Config
from app.database.services.repos import UserRepo, AccountRepo, WorkRepo, PostRepo
from app.handlers.admin.statistic import admin_cmd
from app.handlers.private.menu import select_accounts
from app.handlers.private.parsing import parsing_cmd
from app.handlers.private.posting import posting_cmd, select_executor_work, data_for_instagram_cmd, posting_setting_cmd, \
    select_work_mode
from app.handlers.private.start import start_cmd
from app.handlers.private.statistic import statistic_cmd
from app.keyboard.inline.back import back_cb


async def back_cmd(call: CallbackQuery, callback_data: dict, config: Config, state: FSMContext,
                   user_db: UserRepo, account_db: AccountRepo, work_db: WorkRepo, post_db: PostRepo):
    action = callback_data['action']
    msg = call.message
    if action == 'start':
        await msg.delete()
        await start_cmd(msg, user_db, config, state)
    elif action == 'accounts':
        await select_accounts(call, account_db)
    elif action == 'posting':
        await posting_cmd(call, callback_data, config, account_db, work_db, state)
    elif action == 'parsing':
        await parsing_cmd(call, callback_data, account_db, work_db)
    elif action == 'work':
        await select_executor_work(call, callback_data, account_db, state)
    elif action == 'data_for_inst':
        await data_for_instagram_cmd(call, callback_data, account_db, state)
    elif action == 'settings':
        await posting_setting_cmd(call, callback_data, account_db)
    elif action == 'statistic':
        await statistic_cmd(call, callback_data, account_db, post_db)
    elif action == 'admin':
        await admin_cmd(call, account_db, post_db)



def setup(dp: Dispatcher):
    dp.register_callback_query_handler(back_cmd, back_cb.filter(), state='*')

