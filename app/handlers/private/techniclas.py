from aiogram import Dispatcher
from aiogram.types import CallbackQuery
from babel.dates import format_date

from app.config import Config
from app.database.models import Account
from app.database.services.enums import AccountTypeEnum, AccountStatusEnum
from app.database.services.repos import AccountRepo
from app.filters import IsAdminFilter
from app.handlers.private.decorator import construct_accounts_list
from app.keyboard.inline.accounts import technicals_kb, account_cb
from app.keyboard.inline.admin import admin_cb
from app.misc.times import localize


async def technicals_cmd(call: CallbackQuery, callback_data: dict, account_db: AccountRepo):
    technicals = await account_db.get_accounts_type(AccountTypeEnum.TECHNICAL)
    if not technicals:
        await call.answer('Немає акаунтів')
        return
        # return await add_account_posting(call)
    technicals.sort(key=lambda acc: acc.created_at)
    technical_id = technicals[0].account_id if callback_data['action'] == 'tech' else int(callback_data['account_id'])
    technical = await account_db.get_account(technical_id)
    if len(technicals) == 1 and callback_data['action'] == 'pag':
        await call.answer('У вас тільки один акаунт')
        return
    text = (
        f'🗂 [Ваші акаунти | Технічні]\n\n'
        f'{construct_accounts_list(technicals, technical)}\n'
        f'{construct_technicals_text(technical)}'
    )
    if callback_data['action'] == 'tech':
        await call.message.delete()
        msg = await call.message.answer('...')
    else:
        msg = call.message
    await msg.edit_text(text, reply_markup=technicals_kb(technicals, technical))


def setup(dp: Dispatcher):
    dp.register_callback_query_handler(technicals_cmd, IsAdminFilter(), admin_cb.filter(action='tech'), state='*')
    dp.register_callback_query_handler(technicals_cmd, IsAdminFilter(), account_cb.filter(type='tech', action='pag'),
                                       state='*')


def construct_technicals_text(account: Account):
    fmt = '%H:%M:%S'
    text = (
        f'Номер акаунту: {account.account_id}\n'
        f'Статус: <b>{construct_technical_status(account)}</b>\n'
        f'Пароль: {account.password}\n'
        f'Ключ 2Fa: {account.auth_key}\n'
        f'Оновлено: {format_date(account.updated_at, locale="uk_UA")} {localize(account.updated_at).strftime(fmt)}\n'
    )
    return text


def construct_technical_status(account: Account) -> str:
    if account.status == AccountStatusEnum.BANNED:
        return '🟠 Проблеми зі входом'
    else:
        return '🟢 Активний'
