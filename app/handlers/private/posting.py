from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import CallbackQuery, Message
from apscheduler_di import ContextSchedulerDecorator
from babel.dates import format_date

from app.config import Config
from app.database.models import Account, Work
from app.database.services.enums import AccountTypeEnum, AccountStatusEnum, WorkModeEnum, PostStatusEnum
from app.database.services.repos import AccountRepo, WorkRepo, PostRepo, UserRepo
from app.handlers.private.add import add_account_posting
from app.handlers.private.decorator import construct_work_mode, construct_work_status, construct_accounts_list
from app.keyboard import Buttons
from app.keyboard.inline.accounts import customers_kb, account_cb, customer_settings_cb, developer_statistic_kb
from app.keyboard.inline.back import back_keyboard
from app.keyboard.inline.menu import menu_cb
from app.keyboard.inline.moderate import moderate_limit_kb, limit_cb, confirm_moderate_kb, construct_executors_kb, \
    construct_work_mode_kb, add_work_cb, confirm_add_work_kb, delete_work_kb, confirm_delete_work_kb, mod_work_cb, \
    edit_login_data_kb
from app.misc.times import localize
from app.states.accounts import LastNSG, InstagramDataSG


async def posting_cmd(call: CallbackQuery, callback_data: dict, config: Config, account_db: AccountRepo,
                      work_db: WorkRepo, state: FSMContext):
    data = await state.get_data()
    user_id = data['user_id'] if 'user_id' in data.keys() else call.from_user.id
    customers = await account_db.get_accounts_by_user(user_id, AccountTypeEnum.POSTING)
    if not customers:
        return await add_account_posting(call)
    customers.sort(key=lambda acc: acc.created_at)
    customer_id = int(callback_data['account_id']) if 'account_id' in list(callback_data.keys()) else customers[0].account_id
    customer = await account_db.get_account(customer_id)
    works = await work_db.get_work_customer(customer.account_id)
    if len(customers) == 1 and callback_data['action'] == 'pag':
        await call.answer('У вас тільки один акаунт')
        return
    text = (
        f'🗂 [Ваші акаунти | Для публікації]\n\n'
        f'{construct_accounts_list(customers, customer)}\n'
        f'{construct_customer_text(customer)}'
        f'{await construct_customer_works(customer, works, account_db)}\n'
    )
    if customer.status == AccountStatusEnum.UNPAID:
        text += '<b>Термін дії вашої підписки закінчився. Публікація постів була призупинена...</b>'
    if customer.status == AccountStatusEnum.BANNED:
        text += (
            f'<b>Публікація постів зупинена через  проблему зі входом у ваш акаунт Інстаграм.</b>\n\n'
            f'Ви можете змінити дані для входу (пароль, логін, тощо) і відновити публікацію постів самостійно, або '
            f'звернутись за допомогою в чат підтримки.'
        )
    dev = call.from_user.id in config.bot.admin_ids
    await call.message.edit_text(text, reply_markup=customers_kb(customers, customer, dev, bool(works)))


async def posting_setting_cmd(call: CallbackQuery, callback_data: dict, account_db: AccountRepo):
    customer_id = int(callback_data['account_id'])
    customer = await account_db.get_account(customer_id)
    text = (
        f'🗂 [Для публікації | {Buttons.accounts.settings}]\n\n'
        f'Тут ви можете налаштувати роботу вашого акаунту <b>{customer.username}.</b>\n\n'
        f'Ліміт публікацій. Змінити ліміт постів, що публікуються за один день\n\n'
        f'Дані для Інстаграм. Змінити логін, пароль або код двоетапної перевірки\n\n'
        f'Зупинити або запустити. Для зупинки або відновлення публікацій постів на акаунті\n\n'
        f'Видатити. Для видалення акаунта і прив\'язаних постів'
    )
    await call.message.edit_text(text, reply_markup=customer_settings_cb(customer))


async def developer_settings(call: CallbackQuery, callback_data: dict, account_db: AccountRepo,
                             user_db: UserRepo, post_db: PostRepo):
    customer_id = int(callback_data['account_id'])
    customer = await account_db.get_account(customer_id)
    user = await user_db.get_user(customer.user_id)
    fmt = '%H:%M:%S'
    text = (
        f'🗂 [Для публікації | {Buttons.accounts.developer}]\n\n'
        f'Юзернейм: {customer.username}\n'
        f'Пароль: {customer.password}\n'
        f'Ключ 2Fa: {customer.auth_key}\n'
        f'Ліміт в день: {customer.limit}\n'
        f'Аккаунт id: {customer.account_id}\n'
        f'Вільних дій: {customer.free_action}\n'
        f'Створено: {format_date(customer.created_at, locale="uk_UA")} {localize(customer.created_at).strftime(fmt)}\n'
        f'Оновлено: {format_date(customer.updated_at, locale="uk_UA")} {localize(customer.updated_at).strftime(fmt)}\n'
        f'К-ть днів у підписці: {customer.subscript_days}\n'
        f'Користувач: <a href="tg://user?id={user.user_id}">{user.full_name}</a>'
    )
    plan_download_posts = await post_db.get_posts_customer(customer_id, PostStatusEnum.PLAN_DOWNLOAD)
    wait_public_posts = await post_db.get_posts_customer(customer_id, PostStatusEnum.WAIT_PUBLIC)
    detail_statistic = any(list(map(bool, [plan_download_posts + wait_public_posts])))
    if customer.subscript_date:
        text += f'Оплачено: {format_date(customer.subscript_date, locale="uk_UA")} ' \
                f'{localize(customer.subscript_date).strftime(fmt)}\n'
    await call.message.edit_text(text, reply_markup=developer_statistic_kb(customer, user, detail_statistic))


async def limit_cmd(call: CallbackQuery, callback_data: dict, account_db: AccountRepo):
    customer_id = int(callback_data['account_id'])
    customer = await account_db.get_account(customer_id)
    action = callback_data['action']
    if action == 'set':
        await account_db.update_account(customer_id, limit=int(callback_data['val']))
    elif action == 'plus':
        if customer.limit + int(callback_data['val']) > 50:
            await call.answer('Ви досягли максимального ліміту, 50 постів в день', show_alert=True)
            return
        await account_db.update_account(customer_id, limit=customer.limit + int(callback_data['val']))
    elif action == 'minus':
        if customer.limit - int(callback_data['val']) <= 0:
            await call.answer('Ви досягли мінімального ліміту, 1 пост в день', show_alert=True)
            return
        await account_db.update_account(customer_id, limit=customer.limit - int(callback_data['val']))
    customer = await account_db.get_account(customer_id)
    text = (
        f'🗂 [Для публікації | {Buttons.accounts.limit}]\n\n'
        f'Встановіть ліміт публікацій. Це максимальне число постів, які можуть бути '
        f'опубліковані на вашому акаунті <b>{customer.username}</b>.\n\nЗверність увагу, '
        f'адміністрація сервісу не рекомендує збільшувати ліміт вище стандартного (25) '
        f'у разі, якщо ваш акаунт був створений менше ніж 2 місяці тому.\n\n'
        f'Поточний ліміт публікацій: <b>{customer.limit} постів за день.</b>'
    )
    await call.message.edit_text(text, reply_markup=moderate_limit_kb(customer))


async def confirm_pause_cmd(call: CallbackQuery, callback_data: dict, account_db: AccountRepo):
    customer_id = int(callback_data['account_id'])
    customer = await account_db.get_account(customer_id)
    if customer.status == AccountStatusEnum.BANNED:
        await call.answer('Ця функція доступна лише для акаунтів, які НЕ мають статус "Активний"', show_alert=True)
        return
    text = (
        f'🗂 [Для публікації | {Buttons.accounts.pause}]\n\n'
        f'Ця функція зупинить публікацію постів для вашого акаунту <b>{customer.username}</b>.\n\n'
        '<b>Ви бажаєте зупинити акаунт?</b>'
    )
    await call.message.edit_text(text, reply_markup=confirm_moderate_kb(customer, 'pause'))


async def confirm_delete_cmd(call: CallbackQuery, callback_data: dict, account_db: AccountRepo):
    customer_id = int(callback_data['account_id'])
    customer = await account_db.get_account(customer_id)
    text = (
        f'🗂 [Для публікації | {Buttons.accounts.delete}]\n\n'
        f'Ця дія призведе до незворотнього видалення всіх даних від вашого акаунту, '
        f'а також збережених постів.\n\n'
        '<b>Ви бажаєте видлити акаунт?</b>'
    )
    await call.message.edit_text(text, reply_markup=confirm_moderate_kb(customer, 'delete'))


async def delete_account_cmd(call: CallbackQuery, callback_data: dict, account_db: AccountRepo, work_db: WorkRepo,
                             post_db: PostRepo, config: Config, scheduler: ContextSchedulerDecorator):
    customer_id = int(callback_data['account_id'])
    customer = await account_db.get_account(customer_id)
    works = await work_db.get_work_customer(customer_id)
    for work in works:
        posts = await post_db.get_post_work(work.work_id)
        for post in posts:
            post.delete_me(config)
            post.delete_my_job(scheduler)
            await post_db.delete_post(post.post_id)
        await work_db.delete_work(work.work_id)
    text = (
        f'🗂 [Для публікації | {Buttons.accounts.delete}]\n\n'
        f'Ваш акаунт {customer.username} був видалений\n\n'
        f'Дані для входу в Інстаграм від вашого акаунту\n\n'
        f'Пароль: {customer.password}\n'
    )
    if customer.auth_key:
        text += (
            f'Ключ двоетапної перевірки: {customer.auth_key}'
        )
    await account_db.delete_account(customer_id)
    await call.answer('Акаунт був видалений', show_alert=True)
    await call.message.edit_text(text, reply_markup=back_keyboard())


async def pause_cmd(call: CallbackQuery, callback_data: dict, account_db: AccountRepo,
                    post_db: PostRepo, scheduler: ContextSchedulerDecorator):
    customer_id = int(callback_data['account_id'])
    customer = await account_db.get_account(customer_id)
    await account_db.update_account(customer_id, status=AccountStatusEnum.PAUSE)
    for post in await post_db.get_posts_account(customer_id):
        if post.job_id and scheduler.get_job(post.job_id):
            scheduler.get_job(post.job_id).resume()
    text = (
        f'Ви зупинили усі дії для вашого акаунту {customer.username} ✔'
    )
    await call.answer(text, show_alert=True)
    await posting_setting_cmd(call, callback_data, account_db)


async def confirm_resume_cmd(call: CallbackQuery, callback_data: dict, account_db: AccountRepo):
    customer_id = int(callback_data['account_id'])
    customer = await account_db.get_account(customer_id)
    text = (
        f'🗂 [Для публікації | {Buttons.accounts.resume}]\n\n'
        f'Ви дійсно бажаєте відновити публікацію постів '
        f'для вашого акаунту <b>{customer.username}</b>?'
    )
    await call.message.edit_text(text, reply_markup=confirm_moderate_kb(customer, 'resume'))


async def resume_cmd(call: CallbackQuery, callback_data: dict, account_db: AccountRepo):
    customer_id = int(callback_data['account_id'])
    customer = await account_db.get_account(customer_id)
    await account_db.update_account(customer_id, status=AccountStatusEnum.ACTIVE)
    text = (
        f'Ви відновили публікацію постів для вашого акаунту {customer.username} ✔'
    )
    await call.answer(text, show_alert=True)
    await posting_setting_cmd(call, callback_data, account_db)


async def select_executor_work(call: CallbackQuery, callback_data: dict, account_db: AccountRepo, state: FSMContext):
    await state.finish()
    customer_id = int(callback_data['account_id'])
    customer = await account_db.get_account(customer_id)
    executors = await account_db.get_accounts_by_user(call.from_user.id, AccountTypeEnum.PARSING)
    text = (
        f'🗂 [Для публікації | {Buttons.accounts.add_work}]\n\n'
        f'Додайте завдання для вашого акаунту <b>{customer.username}</b>\n\n'
        f'Оберіть акаунт, з якого будуть копіюватись пости 👇'
    )
    await call.message.edit_text(text, reply_markup=construct_executors_kb(executors, customer))


async def select_work_mode(call: CallbackQuery, callback_data: dict, account_db: AccountRepo):
    customer_id = int(callback_data['account_id'])
    executor_id = int(callback_data['executor_id'])
    customer = await account_db.get_account(customer_id)
    executor = await account_db.get_account(executor_id)
    text = (
        f'🗂 [Для публікації | {Buttons.accounts.add_work}]\n\n'
        f'Ви бажаєте додати завдання на ваш акаунт <b>{customer.username}</b>\n\n'
        f'Оберіть вид постів які будуть скопійовані з {executor.username} 👇'
    )
    await call.message.edit_text(text, reply_markup=construct_work_mode_kb(executor, customer))


async def confirm_add_work(call: CallbackQuery, callback_data: dict, account_db: AccountRepo, work_db: WorkRepo,
                           state: FSMContext):
    customer_id = int(callback_data['account_id'])
    executor_id = int(callback_data['executor_id'])
    customer = await account_db.get_account(customer_id)
    executor = await account_db.get_account(executor_id)
    mode = callback_data['mode']
    works = await work_db.get_custom_work(customer_id, executor_id, get_work_enum(mode, disable_last_n=True))
    if works:
        text = (
            'Таке завдання вже існує, ви зможете додати нове завдання, коли попереднє буде видалене.'
        )
        await call.answer(text, show_alert=True)
        return
    if mode == 'last_n':
        text = (
            f'🗂 [Для публікації | {Buttons.accounts.add_work}]\n\n'
            f'Відправте число останніх постів які треба скопіювати 👇'
        )
        last_msg = await call.message.edit_text(text)
        await state.update_data(executor_id=executor_id, customer_id=customer_id, last_msg_id=last_msg.message_id)
        await LastNSG.Input.set()
        return
    text = (
        f'🗂 [Для публікації | {Buttons.accounts.add_work}]\n\n'
        f'Ви обрали: <b>Скопіювати {get_work_mode(mode, 0).lower()} з {executor.username}</b>\n\n'
        f'Підтвердіть додавання завдання для <b>{customer.username}</b>'
    )
    await call.message.edit_text(text, reply_markup=confirm_add_work_kb(executor, customer, mode))


async def save_work_limit(msg: Message, state: FSMContext, account_db: AccountRepo):
    await msg.delete()
    data = await state.get_data()
    limit = str(msg.text).strip()
    error_text = (
        f'🗂 [Для публікації | {Buttons.accounts.add_work}]\n\n'
        f'error_message\n\n'
        f'Відправте число останніх постів які треба скопіювати 👇'
    )
    if 'last_msg_id' in list(data.keys()):
        await msg.bot.delete_message(msg.from_user.id, data['last_msg_id'])
    if not limit.isnumeric():
        error_text = error_text.replace('error_message', 'Не схоже на число, спробуйте ще раз')
        last_msg = await msg.answer(error_text)
        await state.update_data(last_msg_id=last_msg.message_id)
        return
    elif int(limit) > 1000:
        error_text = error_text.replace('error_message', 'Максимальна кількість постів 1000')
        last_msg = await msg.answer(error_text)
        await state.update_data(last_msg_id=last_msg.message_id)
        return
    limit = int(limit)
    customer_id = data['customer_id']
    executor_id = data['executor_id']
    customer = await account_db.get_account(customer_id)
    executor = await account_db.get_account(executor_id)
    text = (
        f'🗂 [Для публікації | {Buttons.accounts.add_work}]\n\n'
        f'Ви обрали: <b>Скопіювати {get_work_mode("last_n", limit).lower()} з {executor.username}</b>\n\n'
        f'Підтвердіть додавання завдання для <b>{customer.username}</b>'
    )
    await msg.answer(text, reply_markup=confirm_add_work_kb(executor, customer, 'last_n'))
    await state.update_data(limit=limit)


async def create_work_cmd(call: CallbackQuery, callback_data: dict, config: Config, account_db: AccountRepo,
                          work_db: WorkRepo, state: FSMContext):
    data = await state.get_data()
    customer_id = int(callback_data['account_id'])
    executor_id = int(callback_data['executor_id'])
    mode = callback_data['mode']
    limit = data['limit'] if 'limit' in list(data.keys()) else 0
    mode_enum = get_work_enum(mode)
    await work_db.add(
        mode=mode_enum, limit=limit, user_id=call.from_user.id,
        customer_id=customer_id, executor_id=executor_id
    )
    await call.answer('Завдання успішно додано', show_alert=True)
    await posting_cmd(call, callback_data, config, account_db, work_db, state)
    await state.finish()


async def delete_work_cmd(call: CallbackQuery, callback_data: dict, account_db: AccountRepo, work_db: WorkRepo,
                          state: FSMContext):
    customer_id = int(callback_data['account_id'])
    customer = await account_db.get_account(customer_id)
    text = (
        f'🗂 [Для публікації | {Buttons.accounts.del_work}]\n\n'
    )
    customer_works = await work_db.get_work_customer(customer_id)
    if not customer_works:
        await call.answer('У вас немає завдань на цьому акаунті')
        await select_executor_work(call, callback_data, account_db, state)
        return
    for work, num in zip(customer_works, range(1, len(customer_works)+1)):
        executor = await account_db.get_account(work.executor_id)
        text += f'{num}. {construct_work_mode(work)} з {executor.username}\n'
    text += f'\nВиберіть завдання, яке потрібно видалити <b>{customer.username}</b> 👇'
    await call.message.edit_text(text, reply_markup=delete_work_kb(customer_works, customer))


async def confirm_delete_work(call: CallbackQuery, callback_data: dict, work_db: WorkRepo, account_db: AccountRepo):
    work_id = int(callback_data['work_id'])
    customer_id = int(callback_data['account_id'])
    work = await work_db.get_work(work_id)
    customer = await account_db.get_account(customer_id)
    executor = await account_db.get_account(work.executor_id)
    text = (
        f'🗂 [Для публікації | {Buttons.accounts.del_work}]\n\n'
        f'<b>{construct_work_mode(work)} з {executor.username}</b>\n\n'
        f'Підтвердіть видалення завдання: 👇'
    )
    await call.message.edit_text(text, reply_markup=confirm_delete_work_kb(work, customer))


async def delete_work(call: CallbackQuery, callback_data: dict, work_db: WorkRepo, account_db: AccountRepo,
                      post_db: PostRepo, scheduler: ContextSchedulerDecorator, config: Config, state: FSMContext):
    work_id = int(callback_data['work_id'])
    await work_db.delete_work(work_id)
    for post in await post_db.get_post_work(work_id):
        if post.job_id and scheduler.get_job(post.job_id):
            scheduler.get_job(post.job_id).remove()
        post.delete_me(config)
        await post_db.delete_post(post.post_id)
    await call.answer('Завдання було успішно видалено', show_alert=True)
    await posting_cmd(call, callback_data, config, account_db, work_db, state)


async def data_for_instagram_cmd(call: CallbackQuery, callback_data: dict, account_db: AccountRepo, state: FSMContext):
    customer_id = int(callback_data['account_id'])
    customer = await account_db.get_account(customer_id)
    auth_key = 'Відсутній' if not customer.auth_key else f'\n{customer.auth_key}'
    text = (
        f'🗂 [Для публікації | {Buttons.accounts.login_data}]\n\n'
        f'<b>Юзернейм:</b> {customer.username}\n'
        f'<b>Пароль:</b> {customer.password}\n'
        f'<b>Ключ двоетапної перевірки:</b> {auth_key}\n\n'
        f'Ви можете змінити будь які з даних для входу в Інстаграм, натиснувши '
        f'на кнопку нижче 👇'
    )
    await call.message.edit_text(text, reply_markup=edit_login_data_kb(customer))
    await state.update_data(customer_id=customer_id)


async def input_username(call: CallbackQuery, callback_data: dict, state: FSMContext):
    customer_id = int(callback_data['account_id'])
    text = (
        f'🗂 [Для публікації | {Buttons.accounts.login_data}]\n\n'
        f'Відправте <b>новий юзернейм</b> текстовим повідомленням 👇'
    )
    msg = await call.message.edit_text(text, reply_markup=back_keyboard('Відмінити', 'data_for_inst', customer_id))
    await state.update_data(last_msg_id=msg.message_id, key='username', key_name='Юзернейм')
    await InstagramDataSG.Input.set()


async def input_password(call: CallbackQuery, callback_data: dict, state: FSMContext):
    customer_id = int(callback_data['account_id'])
    text = (
        f'🗂 [Для публікації | {Buttons.accounts.login_data}]\n\n'
        f'Відправте <b>новий пароль</b> текстовим повідомленням 👇'
    )
    msg = await call.message.edit_text(text, reply_markup=back_keyboard('Відмінити', 'data_for_inst', customer_id))
    await state.update_data(last_msg_id=msg.message_id, key='password', key_name='Пароль')
    await InstagramDataSG.Input.set()


async def input_auth_key(call: CallbackQuery, callback_data: dict, state: FSMContext):
    customer_id = int(callback_data['account_id'])
    text = (
        f'🗂 [Для публікації | {Buttons.accounts.login_data}]\n\n'
        f'Відправте <b>новий ключ двоетапної перевірки</b> текстовим повідомленням 👇'
    )
    msg = await call.message.edit_text(text, reply_markup=back_keyboard('Відмінити', 'data_for_inst', customer_id))
    await state.update_data(last_msg_id=msg.message_id, key='auth_key', key_name='Код двоетапної перевірки')
    await InstagramDataSG.Input.set()


async def save_account_data(msg: Message, state: FSMContext, account_db: AccountRepo):
    await msg.delete()
    data = await state.get_data()
    customer_id = data['customer_id']
    last_msg_id = data['last_msg_id']
    key_name = data['key_name']
    key = data['key']
    await account_db.update_account(customer_id, **{key: msg.text})
    await msg.bot.delete_message(msg.from_user.id, last_msg_id)
    text = (
        f'🗂 [Для публікації | {Buttons.accounts.login_data}]\n\n'
        f'{key_name} змінено на: {msg.text} ✔'
    )
    await msg.answer(text, reply_markup=back_keyboard(action='data_for_inst', account_id=customer_id))


def setup(dp: Dispatcher):
    dp.register_message_handler(save_work_limit, state=LastNSG.Input)
    dp.register_message_handler(save_account_data, state=InstagramDataSG.Input)

    dp.register_callback_query_handler(data_for_instagram_cmd, account_cb.filter(action='login_data'), state='*')
    dp.register_callback_query_handler(input_username, account_cb.filter(action='edit_username'), state='*')
    dp.register_callback_query_handler(input_password, account_cb.filter(action='edit_password'), state='*')
    dp.register_callback_query_handler(input_auth_key, account_cb.filter(action='edit_auth'), state='*')

    dp.register_callback_query_handler(create_work_cmd, add_work_cb.filter(action='confirm'), state='*')
    dp.register_callback_query_handler(confirm_add_work, add_work_cb.filter(action='mode'), state='*')
    dp.register_callback_query_handler(delete_work_cmd, account_cb.filter(action='del_work'), state='*')
    dp.register_callback_query_handler(confirm_delete_work, mod_work_cb.filter(action='delete'), state='*')
    dp.register_callback_query_handler(delete_work, mod_work_cb.filter(action='conf_delete'), state='*')

    dp.register_callback_query_handler(confirm_pause_cmd, account_cb.filter(action='pause'), state='*')
    dp.register_callback_query_handler(confirm_resume_cmd, account_cb.filter(action='resume'), state='*')
    dp.register_callback_query_handler(resume_cmd, account_cb.filter(action='conf_resume'), state='*')
    dp.register_callback_query_handler(pause_cmd, account_cb.filter(action='conf_pause'), state='*')

    dp.register_callback_query_handler(confirm_delete_cmd, account_cb.filter(action='delete'), state='*')
    dp.register_callback_query_handler(delete_account_cmd, account_cb.filter(action='conf_delete'), state='*')

    dp.register_callback_query_handler(posting_setting_cmd, account_cb.filter(action='settings'), state='*')
    dp.register_callback_query_handler(developer_settings, account_cb.filter(action='dev'), state='*')
    dp.register_callback_query_handler(limit_cmd, account_cb.filter(action='limit'), state='*')
    dp.register_callback_query_handler(limit_cmd, limit_cb.filter(), state='*')
    dp.register_callback_query_handler(select_executor_work, account_cb.filter(action='add_work'), state='*')
    dp.register_callback_query_handler(select_work_mode, add_work_cb.filter(action='select'), state='*')

    dp.register_callback_query_handler(posting_cmd, menu_cb.filter(action='posting'), state='*')
    dp.register_callback_query_handler(posting_cmd, account_cb.filter(type='posting', action='pag'), state='*')
    dp.register_callback_query_handler(posting_cmd, account_cb.filter(type='posting', action='back'), state='*')


def construct_customer_text(account: Account):
    text = (
        f'Номер акаунту: {account.account_id}\n'
        f'Статус: <b>{construct_customer_status(account)}</b>\n'
        f'Ліміт публікацій: {account.limit} постів в день\n'
    )
    return text


def construct_customer_status(account: Account) -> str:
    if account.status == AccountStatusEnum.BANNED:
        return '🟠 Проблеми зі входом'
    elif account.status == AccountStatusEnum.ACTIVE:
        return '🟢 Активний'
    elif account.status == AccountStatusEnum.PAUSE:
        return '🔵 Публікації призупинені'
    elif account.status == AccountStatusEnum.UNPAID:
        return '🔒 Підписка скінчилась'


async def construct_customer_works(account: Account, works: list[Work], account_db: AccountRepo) -> str:
    text = f'🔗 Завдання для цього акаунту:'
    if not works:
        return text + ' Не знайдено'
    else:
        text += '\n'
    for work, num in zip(works, range(1, len(works) + 1)):
        executor = await account_db.get_account(work.executor_id)
        text += f'  {num}. {executor.username} ({construct_work_mode(work)} {construct_work_status(work)})\n'
    return text


def get_work_mode(mode: str, limit: int):
    if mode == 'all':
        return Buttons.accounts.work.all
    elif mode == 'all_and_new':
        return Buttons.accounts.work.all_and_new + ' пости'
    elif mode == 'only_new':
        return Buttons.accounts.work.only_new + ' пости'
    elif mode == 'last_n':
        return Buttons.accounts.work.last_n.replace('X', str(limit))


def get_work_enum(mode: str, disable_last_n: bool = False):
    if mode == 'all_and_new':
        return WorkModeEnum.ALL_AND_NEW
    elif mode == 'only_new':
        return WorkModeEnum.ONLY_NEW
    elif mode == 'all':
        return WorkModeEnum.ALL
    else:
        if not disable_last_n:
            return WorkModeEnum.LAST_N
