import os
from datetime import timedelta

import matplotlib.pyplot as plt
from aiogram import Dispatcher
from aiogram.dispatcher.filters import Command
from aiogram.types import Message, InputFile, CallbackQuery
from matplotlib.axes import Axes

from app.database.models import Account
from app.database.models.base import TimedBaseModel
from app.database.services.enums import AccountTypeEnum, PostStatusEnum, UserStatusEnum, AccountStatusEnum
from app.database.services.repos import AccountRepo, PostRepo, UserRepo
from app.instagram.proxy import ProxyController
from app.keyboard import Buttons
from app.keyboard.inline.admin import admin_kb, admin_cb
from app.keyboard.inline.menu import menu_cb
from app.misc.times import now, localize
import psutil
plt.set_loglevel('WARNING')


async def admin_cmd(call: CallbackQuery, account_db: AccountRepo, post_db: PostRepo,
                    user_db: UserRepo, controller: ProxyController):
    await call.message.delete()
    msg = await call.message.answer('Збираю статистику...')
    text = (
        f'[Панель адміністратора | {Buttons.accounts.statistic}]\n\n'
        f'🖥 Дані з серверу:\n\n'
        f'Оперативна пам\'ять: <b>{memory_usage()}</b>\n\n'
        f'🙎‍♂🙍‍♀ Дані про користувачів:\n\n'
        f'<b>{await users_statistic(user_db)}</b>\n\n'
        f'🗂 Акаунти:\n\n'
        f'<b>{await accounts_statistic(account_db)}</b>\n\n'
        f'📬 Пости:\n\n'
        f'<b>{await posts_statistic(post_db)}</b>\n\n'
        f'🌍 Проксі:\n\n'
        f'{controller.proxy_statistic()}'
    )
    await matplotlib_data(post_db, account_db)
    await msg.bot.send_chat_action(call.from_user.id, 'upload_photo')
    await call.message.answer_photo(InputFile('statistic.png'), caption=text, reply_markup=admin_kb())
    await msg.delete()
    os.remove('statistic.png')


def setup(dp: Dispatcher):
    dp.register_callback_query_handler(admin_cmd, menu_cb.filter(action='admin'), state='*')
    dp.register_callback_query_handler(admin_cmd, admin_cb.filter(action='update'), state='*')


async def posts_statistic(post_db: PostRepo):
    post_active = len(await post_db.get_posts_status(PostStatusEnum.ACTIVE))
    post_plan_download = len(await post_db.get_posts_status(PostStatusEnum.PLAN_DOWNLOAD))
    post_loading = len(await post_db.get_posts_status(PostStatusEnum.LOADING))
    post_plan_public = len(await post_db.get_posts_status(PostStatusEnum.PLAN_PUBLIC))
    post_wait_public = len(await post_db.get_posts_status(PostStatusEnum.WAIT_PUBLIC))
    post_public = len(await post_db.get_posts_status(PostStatusEnum.DONE))
    return (
        f'Активних: {post_active}\n'
        f'Заплановано для скачування: {post_plan_download}\n'
        f'Завантажуються зараз: {post_loading}\n'
        f'Планується час публікації: {post_plan_public}\n'
        f'Очікується публікація: {post_wait_public}\n'
        f'Опубліковані: {post_public}'
    )


async def users_statistic(user_db: UserRepo):
    users = len(await user_db.get_all())
    users_trial = len(await user_db.get_users_status(UserStatusEnum.TRIAL))
    users_active = len(await user_db.get_users_status(UserStatusEnum.ACTIVE))
    return (
        f'Всього: {users}\n'
        f'З пробним періодом: {users_trial}\n'
        f'З платним періодом: {users_active}'
    )


async def accounts_statistic(account_db: AccountRepo):
    posting = len(await account_db.get_accounts_type(AccountTypeEnum.POSTING))
    active = len(await account_db.get_accounts_status(AccountTypeEnum.POSTING, AccountStatusEnum.ACTIVE))
    banned = len(await account_db.get_accounts_status(AccountTypeEnum.POSTING, AccountStatusEnum.BANNED))
    unpaid = len(await account_db.get_accounts_status(AccountTypeEnum.POSTING, AccountStatusEnum.UNPAID))
    return (
        f'Акаунти для публікації: {posting}\n'
        f'Активних: {active}\n'
        f'Забанені: {banned}\n'
        f'Неоплачені: {unpaid}'
    )


def memory_usage():
    memory_total = round(psutil.virtual_memory().total / 10 ** 9, 1)
    memory_available = round(psutil.virtual_memory().available / 10 ** 9, 1)
    return f'доступно {memory_available}/{memory_total} Гб'


async def matplotlib_data(post_db: PostRepo, account_db: AccountRepo):
    plt.rcParams['font.family'] = 'serif'
    plt.rcParams['font.serif'] = ['Times New Roman'] + plt.rcParams['font.serif']
    plt.rcParams.update({'font.size': 13})
    fig = plt.figure(figsize=(20, 10), dpi=250)
    ax1 = plt.subplot2grid((2, 2), (0, 0))
    ax2 = plt.subplot2grid((2, 2), (1, 0))
    ax3 = plt.subplot2grid((2, 2), (0, 1), rowspan=2)
    await plot_top_current_posts(ax1, post_db)
    await plot_posts_statistic(ax2, post_db)
    await plot_table_account(ax3, account_db, post_db)
    plt.savefig('statistic.png')


async def plot_posts_statistic(ax: Axes, post_db: PostRepo):
    posts = await post_db.get_all()
    posts_published = await post_db.get_posts_status(PostStatusEnum.DONE)
    plot_data(ax, posts, color='#366ABA', label='Зареєстровані пости сьогодні')
    plot_data(ax, posts_published, color='#2CEA75', label='Опубліковані сьогодні', created_at=False)
    ax.legend()


async def plot_table_account(ax: Axes, account_db: AccountRepo, post_db: PostRepo,
                             title: str = None):
    ax.axis('off')
    set_zero_spines(ax)
    column_widths = [0.1, 0.2, 0.2, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1]
    table = [['ID', 'Акаунт', 'Статус', 'A', 'ПС', 'З', 'ПП', 'ОП', 'О']]
    for customer in await account_db.get_accounts_type(AccountTypeEnum.POSTING):
        a = await post_db.get_posts_customer(customer.account_id, PostStatusEnum.ACTIVE)
        b = await post_db.get_posts_customer(customer.account_id, PostStatusEnum.PLAN_DOWNLOAD)
        c = await post_db.get_posts_customer(customer.account_id, PostStatusEnum.LOADING)
        d = await post_db.get_posts_customer(customer.account_id, PostStatusEnum.PLAN_PUBLIC)
        e = await post_db.get_posts_customer(customer.account_id, PostStatusEnum.WAIT_PUBLIC)
        f = await post_db.get_posts_customer(customer.account_id, PostStatusEnum.DONE)
        table.append(
            [customer.account_id, customer.username, customer.get_status_string()] +
            list(map(len, [a, b, c, d, e, f]))
        )
    table_plot = ax.table(cellText=table, colWidths=column_widths, loc='center')
    ax.set_title(title)
    table_plot.scale(1, 1.5)


def plot_data(ax: Axes, models: list[TimedBaseModel], color: str, label: str, created_at: bool = True):
    set_zero_spines(ax)
    time_format = '%H'
    objects = [
        (localize(obj.created_at) if created_at else localize(obj.updated_at)).strftime(time_format)
        for obj in models if is_created_at.today(obj, created_at)
    ]
    dates = [(is_created_at.today_start() + timedelta(hours=h)).strftime(time_format) for h in range(24)]
    segments = [objects.count(segment) for segment in dates]
    ax.plot(dates, segments, color=color, alpha=1, label=label, antialiased=True)
    ax.scatter(dates, segments, color=color, alpha=1, antialiased=True)
    ax.fill_between(dates, segments, color=color, alpha=0.1)
    ax.grid(alpha=0.5)


class is_created_at:

    @staticmethod
    def today_end():
        return now().replace(hour=23, minute=59, second=59)

    @staticmethod
    def today_start():
        return now().replace(hour=0, minute=0, second=0)

    @staticmethod
    def today(model: TimedBaseModel, created_at: bool = True):
        model_time = model.created_at if created_at else model.updated_at
        return is_created_at.today_start() <= localize(model_time) <= is_created_at.today_end()
        # return model


async def plot_top_current_posts(ax: Axes, post_db: PostRepo):
    set_zero_spines(ax, left=False, bottom=False)
    post_active = await post_db.get_posts_status(PostStatusEnum.ACTIVE)
    post_plan_download = await post_db.get_posts_status(PostStatusEnum.PLAN_DOWNLOAD)
    post_loading = await post_db.get_posts_status(PostStatusEnum.LOADING)
    post_plan_public = await post_db.get_posts_status(PostStatusEnum.PLAN_PUBLIC)
    post_wait_public = await post_db.get_posts_status(PostStatusEnum.WAIT_PUBLIC)
    post_public = await post_db.get_posts_status(PostStatusEnum.DONE)
    posts = {
        'Активні': len(post_active),
        'Планують скачування': len(post_plan_download),
        'Завантажені': len(post_loading),
        'Планується публікація': len(post_plan_public),
        'Очікується публікація': len(post_wait_public),
        'Опубліковані': len(post_public)
    }
    colors = ['#366ABA', '#366ABA', '#366ABA', '#366ABA', '#FFAD3F', '#2CEA75']
    labels = list(map(str, posts.keys()))
    values = list(posts.values())
    max_value = max(values)
    for label in labels[::-1]:
        ax.barh(label, max_value if max_value != 0 else 10, color='white', edgecolor='black')
    for label, value, i in zip(labels[::-1], values[::-1], range(len(posts))):
        ax.barh(label, value, color=colors[::-1][i], edgecolor='black')
    pass


def set_zero_spines(ax: Axes, top: bool = True, right: bool = True, bottom: bool = True, left: bool = True):
    if top:
        ax.spines['top'].set_linewidth(0)
    if right:
        ax.spines['right'].set_linewidth(0)
    if bottom:
        ax.spines['bottom'].set_linewidth(0)
    if left:
        ax.spines['left'].set_linewidth(0)


def over(lst: list, n: int):
    new_lst = [lst[0]]
    for i in range(len(lst)):
        if (i + 1) % n == 0:
            new_lst.append(lst[i])
    return new_lst
