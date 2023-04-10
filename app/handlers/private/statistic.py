from aiogram import Dispatcher
from aiogram.types import CallbackQuery
from apscheduler_di import ContextSchedulerDecorator

from app.database.services.enums import PostStatusEnum
from app.database.services.repos import AccountRepo, PostRepo
from app.keyboard import Buttons
from app.keyboard.inline.accounts import account_cb, update_statistic_kb
from app.keyboard.inline.back import back_keyboard


async def statistic_cmd(call: CallbackQuery, callback_data: dict, account_db: AccountRepo,
                        post_db: PostRepo):
    if callback_data['action'] == 'update_statistic':
        await call.message.delete()
        msg = await call.message.answer('...')
    else:
        msg = call.message
    customer_id = int(callback_data['account_id'])
    customer = await account_db.get_account(customer_id)
    active_posts = await post_db.get_posts_customer(customer_id, PostStatusEnum.ACTIVE)
    plan_download_posts = await post_db.get_posts_customer(customer_id, PostStatusEnum.PLAN_DOWNLOAD)
    plan_public_posts = await post_db.get_posts_customer(customer_id, PostStatusEnum.PLAN_PUBLIC)
    loading_posts = await post_db.get_posts_customer(customer_id, PostStatusEnum.LOADING)
    wait_public_posts = await post_db.get_posts_customer(customer_id, PostStatusEnum.WAIT_PUBLIC)
    published_posts = await post_db.get_posts_customer(customer_id, PostStatusEnum.DONE)
    # paused_posts = await post_db.get_posts_customer(customer_id, PostStatusEnum.PAUSE)

    text = (
        f'🗂 [Для публікації | {Buttons.accounts.statistic}]\n\n'
        f'Знайдено {len(active_posts)} активних постів для вашого акаунту {customer.username}\n\n'
        f'Планується скачування: {len(plan_download_posts)} постів\n'
        f'Завантажується зараз: {len(loading_posts)} постів\n'
        f'Планується час публікації: {len(plan_public_posts)} постів\n'
        f'Опублікуються сьогодні: {len(wait_public_posts)} постів\n'
        f'Опубліковано за весь час: {len(published_posts)} постів\n'
    )
    await msg.edit_text(text, reply_markup=update_statistic_kb(customer_id))


async def detail_statistic_cmd(call: CallbackQuery, callback_data: dict,
                               post_db: PostRepo, scheduler: ContextSchedulerDecorator):
    customer_id = int(callback_data['account_id'])
    plan_download = await post_db.get_posts_customer(customer_id, PostStatusEnum.PLAN_DOWNLOAD)
    wait_public = await post_db.get_posts_customer(customer_id, PostStatusEnum.WAIT_PUBLIC)
    text = f'🗂 [Для публікації | {Buttons.accounts.statistic}]\n\n'
    if plan_download:
        text += '<b>⬇ Пости, що скоро скачаються</b>\n\n'
        for post, num in zip(plan_download[:5], range(1, 6)):
            job = scheduler.get_job(post.job_id)
            if job:
                text += f'{num}. <b>{post.instagram_link()}</b> {job.next_run_time.strftime("%H:%M")}\n'
    if wait_public:
        text += '\nПости, що скоро опублікуються\n'
        for post, num in zip(wait_public[:5], range(1, 6)):
            job = scheduler.get_job(post.job_id)
            if job:
                text += f'{num}. <b>{post.instagram_link()}</b> Завантаження о {job.next_run_time.strftime("%H:%M")}\n'
    await call.message.edit_text(text, reply_markup=back_keyboard(action='statistic', account_id=customer_id))


def setup(dp: Dispatcher):
    dp.register_callback_query_handler(statistic_cmd, account_cb.filter(action='statistic'), state='*')
    dp.register_callback_query_handler(statistic_cmd, account_cb.filter(action='update_statistic'), state='*')
    dp.register_callback_query_handler(detail_statistic_cmd, account_cb.filter(action='detail_statistic'), state='*')
