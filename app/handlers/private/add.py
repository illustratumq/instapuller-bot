import concurrent.futures
from datetime import datetime

import pyotp
from aiogram import Dispatcher, Bot
from aiogram.dispatcher import FSMContext
from aiogram.types import CallbackQuery, Message
from apscheduler_di import ContextSchedulerDecorator

from app.config import Config
from app.database.services.enums import AccountTypeEnum
from app.database.services.repos import AccountRepo, Account
from app.instagram.proxy import ProxyController
from app.instagram.uploader_v2 import InstagramController
from app.keyboard.inline.accounts import add_account_kb, add_accounts_kb, add_account_confirm_kb, customer_add_kb
from app.keyboard.inline.back import back_keyboard
from app.keyboard.inline.menu import menu_cb
from app.misc.times import now, localize
from app.states.accounts import ParsingSG, PostingSG


async def select_account_type(call: CallbackQuery):
    text = (
        '➕ [Додавання акаунту]\n\n'
        'Будь-ласка, оберіть тип акаунту, який ви хочете додати 👇'
    )
    await call.message.edit_text(text, reply_markup=add_accounts_kb)


async def add_username_parsing(call: CallbackQuery, state: FSMContext):
    text = (
        '➕ [Додавання акаунту]\n\n'
        'Будь-ласка, наділшліть <b>юзернейм акаунту Інстаграм</b> з якого будуть '
        'копіюватись пости 👇\n\n'
    )
    msg = await call.message.edit_text(text, reply_markup=back_keyboard('Відмінити', 'parsing'))
    await state.update_data(last_msg_id=msg.message_id)
    await ParsingSG.Login.set()


async def pre_checking_username(msg: Message, state: FSMContext):
    await msg.delete()
    username = msg.text.lower()
    text = (
        '➕ [Додавання акаунту]\n\n'
        f'Ви хочете додати <b>{instagram_link(username)}</b> до списку своїх акаунтів,'
        f'з яких будуть копіюватись пости?\n\n'
        f'Підтвердіть свій вибір 👇'
    )
    last_msg_id = (await state.get_data())['last_msg_id']
    reply_markup = add_account_confirm_kb('parsing', 'parsing')
    msg = await msg.bot.edit_message_text(text, msg.from_user.id, last_msg_id, reply_markup=reply_markup)
    await state.update_data(username=username, last_msg_id=msg.message_id)
    await ParsingSG.Confirm.set()


async def checking_instagram_username_parsing(call: CallbackQuery, state: FSMContext, account_db: AccountRepo,
                                              scheduler: ContextSchedulerDecorator, config: Config,
                                              controller: ProxyController):
    await call.message.delete()
    proxy = controller.get_working_proxy('register')
    if not proxy:
        text = (
            'Нажаль ми не можемо перевірити ваш акаунт на дійсність через тимчасову проблему '
            'з нашими проксі-серверами. Будь ласка зверністья в підтримку, або спробуйте пізніше'
        )
        await call.message.answer_sticker(config.misc.error_sticker_id)
        return await call.message.answer(text)
    proxy = controller.get_working_proxy('register')  # TODO
    data = await state.get_data()
    username = data['username']
    customers = await account_db.get_accounts_by_user(call.from_user.id, AccountTypeEnum.POSTING)
    technicals = await account_db.get_free_technicals()
    sticker_msg = await call.message.answer('🔍')
    last_msg = await call.message.answer('Перевіряю акаунт в Інстаграм. Це може зайняти до 5 хв...')
    concurrent.futures.ThreadPoolExecutor(max_workers=1).submit(
        InstagramController(proxy=proxy).check_parsing_account,
        customers + technicals, username, scheduler, successfully_login_parsing, bad_login_parsing,
        kwargs=dict(bot=call.bot, user_id=call.from_user.id,
                    last_msg_id=[sticker_msg.message_id, last_msg.message_id],
                    username=username, state=state, account_db=account_db)
    )
    await ParsingSG.Check.set()


async def successfully_login_parsing(bot: Bot, last_msg_id: list[int], user_id: int, username: str, state: FSMContext,
                                     account_db: AccountRepo):
    for msg_id in last_msg_id:
        await bot.delete_message(user_id, msg_id)
    await account_db.add(
        user_id=user_id, username=username, type=AccountTypeEnum.PARSING)
    text = (
        f'➕ [Додавання акаунту]\n\n'
        f'✔ Акаунт <b>{username}</b> було успішно перевірено. Тепер ви можете копіювати з нього пости!'
    )
    await bot.send_message(user_id, text,  reply_markup=back_keyboard('◀ До списку акаунтів', 'parsing'))
    await state.finish()


async def bad_login_parsing(bot: Bot, last_msg_id: list[int], user_id: int, username: str, state: FSMContext,
                            account_db: AccountRepo):
    for msg_id in last_msg_id:
        await bot.delete_message(user_id, msg_id)
    text = (
        '➕ [Додавання акаунту]\n\n'
        f'Нажаль я не знайшов <b>{instagram_link(username)}</b> в Інстаграм. Спробуйте ще раз.\n\n'
    )
    msg = await bot.send_message(user_id, text=text, reply_markup=add_account_kb('parsing'))
    await state.update_data(last_msg_id=msg.message_id)
    await state.finish()


async def add_username_posting(call: CallbackQuery, state: FSMContext):
    text = (
        '➕ [Додавання акаунту]\n\n'
        '<b>1)</b> Будь-ласка наділшліть <b>юзернейм</b> акаунту на якому будуть публікуватись пости 👇'
    )
    msg = await call.message.edit_text(text, reply_markup=back_keyboard('Відмінити', 'start'))
    await state.update_data(last_msg_id=msg.message_id)
    await PostingSG.Login.set()


async def add_password_posting(msg: Message, state: FSMContext):
    await msg.delete()
    username = msg.text.lower()
    last_msg_id = (await state.get_data())['last_msg_id']
    text = (
        f'➕ [Додавання акаунту]\n\n'
        f'Юзернейм: <b>{instagram_link(username)}</b>\n\n'
        f'<b>2)</b> Будь-ласка надішліть <b>пароль</b> від акаунту 👇'
    )
    msg = await msg.bot.edit_message_text(text, msg.from_user.id, last_msg_id, text,
                                          reply_markup=back_keyboard('Відмінити', 'accounts'))
    await state.update_data(last_msg_id=msg.message_id, username=username)
    await PostingSG.Password.set()


async def add_auth_posting(msg: Message, state: FSMContext, config: Config):
    await msg.delete()
    password = msg.text
    data = await state.get_data()
    last_msg_id = data['last_msg_id']
    username = data['username']
    guide = (
        'Ключ двоетапної перевірки в Інстаграм - це текстовий ключ, що складається '
        'з 32 літер та цифр. За допомогою ключа, різні додатки можуть генерувати '
        'код з 6-ти цифр, який ви вводите при вході в акаунт.\n\n'
        'Щоб самостійно отримати ключ двоетапної перевірки, <b>обов\'язково ознайомтесь з '
        'інструкцією, натиснувши кнопку нижче.</b> Якщо ви не користуєтесь дфухфакторним '
        'захистом в Інстаграм, пропустіть цей крок.'
    )
    text = (
        f'➕ [Додавання акаунту]\n\n'
        f'Юзернейм: <b>{instagram_link(username)}</b>\n'
        f'Пароль: {password}\n\n'
        f'<b>3)</b> Будь-ласка надішліть <b>ключ двоетапної перевірки</b>'
        f'для входу в акаунт, або пропустіть цей крок 👇\n\n'
    )
    text += guide
    msg = await msg.bot.edit_message_text(text, msg.from_user.id, last_msg_id,
                                          reply_markup=customer_add_kb(config.misc.auth_guide_link))
    await state.update_data(last_msg_id=msg.message_id, password=password, auth=None)
    await PostingSG.Confirm.set()


async def save_auth_key(msg: Message, state: FSMContext, config: Config, scheduler: ContextSchedulerDecorator):
    await msg.delete()
    data = await state.get_data()
    last_msg_id = data['last_msg_id']
    auth_key: str = msg.text.replace(' ', '')
    if not is_valid_authkey(auth_key) or len(auth_key) < 10 or auth_key.isnumeric():
        username = data['username']
        password = data['password']
        text = (
            f'➕ [Додавання акаунту]\n\n'
            f'Юзернейм: <b>{instagram_link(username)}</b>\n'
            f'Пароль: {password}\n\n'
            f'<b>3)</b> Будь-ласка надішліть <b>ключ двоетапної перевірки</b>'
            f'для входу в акаунт, або пропустіть цей крок 👇\n\n'
            f'<i>Надісланий вами ключ {auth_key} не коректний. Будь-ласка ознайомтесь '
            f'з інструкцією, і повторіть спробу.\n\nЯкщо у вас виникли труднощі на цьому етапі,'
            f' напишіть нам в чат підтримки!</i>'
        )
        await msg.bot.edit_message_text(text, msg.from_user.id, last_msg_id,
                                        reply_markup=customer_add_kb(config.misc.auth_guide_link, help=True))
        return
    else:
        auth_code = pyotp.TOTP(auth_key)
        time_remaining = int(auth_code.interval - now().timestamp() % auth_code.interval)
        text = (
            f'Ваш код для входу: <code>{auth_code.now()}</code>, натисніть, щоб скопіювати.\n\n'
            f'🕐 Код буде оновленно через {time_remaining} секунд'
        )
        auth_code_msg = await msg.answer(text)
        await state.update_data(auth_code_msg_id=auth_code_msg.message_id, start_time=now().timestamp())
        job = scheduler.add_job(auth_code_auto_update, trigger='interval', max_instances=2, misfire_grace_time=5,
                                seconds=1, kwargs=dict(msg=msg, auth_key=auth_key, state=state))
        await state.update_data(job_id=job.id, auth_key=auth_key)
        username = data['username']
        password = data['password']
        text = (
            f'➕ [Додавання акаунту]\n\n'
            f'Юзернейм: <b>{instagram_link(username)}</b>\n'
            f'Пароль: {password}\n'
            f'Підтвердіть додавання акаунту 👇'
        )
        await msg.bot.delete_message(msg.from_user.id, last_msg_id)
        msg = await msg.answer(text, reply_markup=add_account_confirm_kb('posting'))
        await state.update_data(last_msg_id=msg.message_id)


async def confirm_add_posting(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    last_msg_id = data['last_msg_id']
    username = data['username']
    password = data['password']
    text = (
        f'➕ [Додавання акаунту]\n\n'
        f'Юзернейм: <b>{instagram_link(username)}</b>\n'
        f'Пароль: {password}\n\n'
        f'Підтвердіть додавання акаунту 👇'
    )
    await state.update_data(job_id=None, auth_key=None)
    await call.message.bot.edit_message_text(text, call.from_user.id, last_msg_id,
                                             reply_markup=add_account_confirm_kb('posting'))


async def checking_instagram_login_posting(call: CallbackQuery, state: FSMContext, account_db: AccountRepo,
                                           scheduler: ContextSchedulerDecorator, config: Config,
                                           controller: ProxyController):
    await call.message.delete()
    data = await state.get_data()
    if scheduler.get_job(data['job_id']):
        scheduler.get_job(data['job_id']).remove()
    proxy = controller.get_working_proxy('register')
    if not proxy:
        text = (
            'Нажаль ми не можемо перевірити ваш акаунт на дійсність через тимчасову проблему '
            'з нашими проксі-серверами. Будь ласка зверністья в підтримку, або спробуйте пізніше'
        )
        await call.message.answer_sticker(config.misc.error_sticker_id)
        return await call.message.answer(text)
    proxy = controller.get_working_proxy('register')  # TODO
    username = data['username']
    password = data['password']
    auth_key = data['auth_key']
    customer = await account_db.add(username=username, password=password, auth_key=auth_key, user_id=call.from_user.id,
                                    type=AccountTypeEnum.POSTING)
    sticker_msg = await call.message.answer('⏳')
    last_msg = await call.message.answer('Пробую увійти в ваш акаунт в Інстаграм. Це може зайняти до 5 хв...')
    concurrent.futures.ThreadPoolExecutor(max_workers=1).submit(
        InstagramController(proxy=proxy).login, customer, scheduler, successfully_login_posting,
        bad_login_posting,
        kwargs=dict(bot=call.bot, user_id=call.from_user.id,
                    last_msg_id=[last_msg.message_id, sticker_msg.message_id],
                    customer=customer, state=state, account_db=account_db)
    )
    await ParsingSG.Check.set()


async def successfully_login_posting(bot: Bot, last_msg_id: list[int], user_id: int, customer: Account, state: FSMContext,
                                     account_db: AccountRepo):
    for msg_id in last_msg_id:
        await bot.delete_message(user_id, msg_id)
    text = (
        f'➕ [Додавання акаунту]\n\n'
        f'✔ Акаунт <b>{customer.username}</b> було успішно перевірено. Тепер ви можете публікувати пости на ньому!'
    )
    await bot.send_message(user_id, text,  reply_markup=back_keyboard('◀ До списку акаунтів', 'accounts'))
    await state.finish()


async def bad_login_posting(bot: Bot, last_msg_id: list[int], user_id: int, customer: Account, state: FSMContext,
                            account_db: AccountRepo):
    for msg_id in last_msg_id:
        await bot.delete_message(user_id, msg_id)
    text = (
        '➕ [Додавання акаунту]\n\n'
        f'Нажаль я не зміг увійти в ваш акаунт <b>{instagram_link(customer.username)}</b> '
        f'в Інстаграм. Спробуйте ще раз.\n\n'
    )
    await account_db.delete_account(customer.account_id)
    msg = await bot.send_message(user_id, text=text, reply_markup=add_account_kb('posting'))
    await state.update_data(last_msg_id=msg.message_id)
    await state.finish()


def setup(dp: Dispatcher):
    dp.register_callback_query_handler(select_account_type, menu_cb.filter(action='add_account'), state='*')
    dp.register_callback_query_handler(add_username_parsing, menu_cb.filter(action='add_parsing'), state='*')
    dp.register_message_handler(pre_checking_username, state=ParsingSG.Login)
    dp.register_callback_query_handler(checking_instagram_username_parsing, menu_cb.filter(action='conf_add_parsing'),
                                       state='*')

    dp.register_callback_query_handler(add_username_posting, menu_cb.filter(action='add_posting'), state='*')
    dp.register_message_handler(add_password_posting, state=PostingSG.Login)
    dp.register_message_handler(add_auth_posting, state=PostingSG.Password)
    dp.register_message_handler(save_auth_key, state=PostingSG.Confirm)
    dp.register_callback_query_handler(confirm_add_posting, menu_cb.filter(action='skip_2fa'), state='*')
    dp.register_callback_query_handler(checking_instagram_login_posting, menu_cb.filter(action='conf_add_posting'),
                                       state='*')


async def add_account_posting(call: CallbackQuery):
    text = (
        '➕ [Додавання акаунту]\n\n'
        'У вас немає жодного акаунту <b>для публікації</b>, '
        'ви можете додати його зараз'
    )
    await call.message.edit_text(text, reply_markup=add_account_kb('posting'))


async def add_account_parsing(call: CallbackQuery):
    text = (
        '➕ [Додавання акаунту]\n\n'
        'У вас немає жодного акаунту <b>для копіювання</b>, '
        'ви можете додати його зараз'
    )
    await call.message.edit_text(text, reply_markup=add_account_kb('parsing'))


def instagram_link(username: str) -> str:
    return f'<a href="https://www.instagram.com/{username}">@{username}</a>'


def is_valid_authkey(key: str) -> bool:
    try:
        pyotp.TOTP(key).now()
        return True
    except:
        return False


async def auth_code_auto_update(msg: Message, auth_key, state: FSMContext, scheduler: ContextSchedulerDecorator):
    data = await state.get_data()
    try:
        start_time = data['start_time']
        auth_code_msg_id = data['auth_code_msg_id']
        auth_code = pyotp.TOTP(auth_key)
        time_remaining = int(auth_code.interval - now().timestamp() % auth_code.interval)
        text = (
            f'Ваш код для входу: <code>{auth_code.now()}</code>, натисніть, щоб скопіювати. '
            f'(Це повідомлення автоматично видалиться через 1 хв)\n\n'
            f'🕐 Код буде оновленно через {time_remaining} секунд. Щоб продовжити підтвердіть додавання акаунту.'
        )
        if (now() - localize(datetime.fromtimestamp(start_time))).seconds >= 60:
            text = (
                'Час очікування вичерпано, щоб отримати код знову, відправте ключ повторно, або скористайтесь '
                'мобільним додатком Google Authenticator.'
            )
            await msg.bot.delete_message(msg.from_user.id, auth_code_msg_id)
            await msg.answer(text)
            scheduler.get_job(data['job_id']).remove()
            return
        await msg.bot.edit_message_text(text, msg.from_user.id, auth_code_msg_id)
    except:
        scheduler.get_job(data['job_id']).remove()
