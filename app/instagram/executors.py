import concurrent.futures
import logging
from datetime import timedelta

from apscheduler_di import ContextSchedulerDecorator
from sqlalchemy.orm import sessionmaker

from app.config import Config
from app.database.models import Post
from app.database.services.enums import AccountTypeEnum, AccountStatusEnum, PostStatusEnum, WorkModeEnum
from app.instagram.misc import get_post_times, calculate_timeout, database, interval, run_time, \
    concatenate_lists, date
from app.instagram.proxy import ProxyController
from app.instagram.uploader_v2 import InstagramController
from app.misc.times import now, localize

log = logging.getLogger(__name__)
format_time = '%H:%M:%S %d.%m.%y'


async def setup_executors(scheduler: ContextSchedulerDecorator, proxy_controller: ProxyController):
    scheduler.ctx.add_instance(proxy_controller, ProxyController)
    scheduler.add_job(register_posts_executor_v2, **interval(60))
    scheduler.add_job(manage_posts_executor_v2, **interval(30))
    scheduler.add_job(public_posts_executor_v2, **interval(55))
    scheduler.add_job(reset_posts_status, **date(10))


async def register_posts_executor_v2(session: sessionmaker, scheduler: ContextSchedulerDecorator,
                                     proxy_controller: ProxyController):
    db = database(session)
    works = await db.work_db.get_work_mode(WorkModeEnum.LAST_N)
    works += await db.work_db.get_work_mode(WorkModeEnum.ALL)
    for work in works:
        technicals = await db.account_db.get_free_technicals()
        customer = await db.account_db.get_account(work.customer_id)
        if customer.status in (AccountStatusEnum.PAUSE, AccountStatusEnum.BANNED):
            pass
        technicals.append(customer)
        proxy = proxy_controller.get_working_proxy()
        # if not proxy:
        #     return
        if False:
            pass
        else:
            executor = await db.account_db.get_account(work.executor_id)
            log_msg = f'Перевірка роботи для {customer.username} з {executor.username}'
            log.warning(log_msg)
            ex = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            ex.submit(InstagramController().get_posts, technicals, executor, work, scheduler)
            return
    await db.close()


async def manage_posts_executor_v2(session: sessionmaker, scheduler: ContextSchedulerDecorator):
    timeout = 50
    db = database(session)
    customers = [customer for customer in await db.account_db.get_accounts_type(AccountTypeEnum.POSTING) if
                 customer.status not in (AccountStatusEnum.PAUSE, AccountStatusEnum.BANNED)]
    posts = [await db.post_db.get_posts_customer(customer.account_id, PostStatusEnum.ACTIVE) for customer in customers]
    posts = concatenate_lists(*posts)
    for post in posts:
        customer = await db.account_db.get_account(post.customer_id)
        loading_posts = await db.post_db.get_posts_customer(customer.account_id, PostStatusEnum.LOADING)
        plan_download_posts = await db.post_db.get_posts_customer(customer.account_id, PostStatusEnum.PLAN_DOWNLOAD)
        plan_public_posts = await db.post_db.get_posts_customer(customer.account_id, PostStatusEnum.PLAN_PUBLIC)
        wait_public_posts = await db.post_db.get_posts_customer(customer.account_id, PostStatusEnum.WAIT_PUBLIC)
        counter = sum(len(i) for i in (loading_posts, plan_download_posts, plan_public_posts, wait_public_posts))
        need_to_download = customer.limit - counter
        if need_to_download > 0:
            log.warning(
                f'{customer.limit} - {len(loading_posts)} - {len(plan_download_posts)} - {len(plan_public_posts)} '
                f'- {len(wait_public_posts)} = {need_to_download}'
            )
            times = get_post_times(plan_download_posts, scheduler)
            if not times or max(times) < now():
                next_run_time = now() + timedelta(seconds=60)
            else:
                next_run_time = max(times) + timedelta(seconds=timeout)
            download_job = scheduler.add_job(
                name=f'Скачування поста {post.post_id} ({customer.username}) в {next_run_time.strftime(format_time)}',
                **run_time(next_run_time), func=pre_download_post,
                kwargs=dict(post=post))
            await db.post_db.update_post(post.post_id, status=PostStatusEnum.PLAN_DOWNLOAD, job_id=download_job.id)
            log_msg = (
                f'Завантаження поста {post.post_id} для {customer.username} '
                f'заплановано на {next_run_time.strftime(format_time)}. '
            )
            log.warning(log_msg)
    await db.close()


async def public_posts_executor_v2(session: sessionmaker, scheduler: ContextSchedulerDecorator, config: Config):
    db = database(session)
    customers = [customer for customer in await db.account_db.get_accounts_type(AccountTypeEnum.POSTING) if
                 customer.status not in (AccountStatusEnum.PAUSE, AccountStatusEnum.BANNED)]
    for customer in customers:
        posts = await db.post_db.get_posts_customer(customer.account_id, PostStatusEnum.PLAN_PUBLIC)
        for post in posts:
            wait_public_posts = await db.post_db.get_posts_customer(customer.account_id, PostStatusEnum.WAIT_PUBLIC)
            published_posts = await db.post_db.get_posts_customer(customer.account_id, PostStatusEnum.DONE)
            today_published_posts = [post for post in published_posts
                                     if localize(post.updated_at).strftime('%d.%m.%y') == now().strftime('%d.%m.%y')]
            need_to_public = customer.limit - len(wait_public_posts) - len(today_published_posts)
            log.warning(
                f'{customer.limit} - {len(wait_public_posts)} - {len(today_published_posts)} = {need_to_public}')
            if need_to_public > 0:
                if not post.is_am_downloaded(config) or post.mediacount == 0:
                    post.delete_me(config)
                    await db.post_db.update_post(post.post_id, status=PostStatusEnum.ACTIVE)
                else:
                    times = get_post_times(wait_public_posts, scheduler)
                    if not times or max(times) < now():
                        next_run_time = now() + timedelta(seconds=60)
                    else:
                        next_run_time = max(times) + timedelta(seconds=calculate_timeout(customer.limit))
                    public_job = scheduler.add_job(
                        name=f'Публікація поста {post.post_id} в {next_run_time.strftime(format_time)}',
                        **run_time(next_run_time), func=pre_upload_post, kwargs=dict(post=post)
                    )
                    await db.post_db.update_post(post.post_id, status=PostStatusEnum.WAIT_PUBLIC, job_id=public_job.id)
                    # await db.account_db.update_account(customer.account_id, free_action=customer.free_action - 1)
                    log_msg = (
                        f'Публікація поста {post.post_id} для {customer.username} заплановано на '
                        f'{next_run_time.strftime(format_time)}'
                    )
                    log.warning(log_msg)


async def pre_download_post(session: sessionmaker, post: Post, proxy_controller: ProxyController,
                            scheduler: ContextSchedulerDecorator):
    db = database(session)
    customer = await db.account_db.get_account(post.customer_id)
    proxy = proxy_controller.get_working_proxy()
    if customer.status in (AccountStatusEnum.PAUSE, AccountStatusEnum.BANNED):
        await db.post_db.update_post(post.post_id, status=PostStatusEnum.ACTIVE)
    # elif not proxy:
    #     await db.post_db.update_post(post.post_id, status=PostStatusEnum.ACTIVE)
    else:
        technicals = await db.account_db.get_free_technicals()
        technicals.append(customer)
        ex = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        ex.submit(InstagramController().download_post, technicals, post, scheduler)
        #  TODO: set proxy
    await db.close()


async def pre_upload_post(session: sessionmaker, post: Post, proxy_controller: ProxyController,
                          scheduler: ContextSchedulerDecorator):
    db = database(session)
    customer = await db.account_db.get_account(post.customer_id)
    proxy = proxy_controller.get_working_proxy()
    if customer.status in (AccountStatusEnum.PAUSE, AccountStatusEnum.BANNED):
        await db.post_db.update_post(post.post_id, status=PostStatusEnum.PLAN_PUBLIC)
    # elif not proxy:
    #     await db.post_db.update_post(post.post_id, status=PostStatusEnum.PLAN_PUBLIC)
    else:
        ex = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        ex.submit(InstagramController().upload, customer, post, scheduler)
        # TODO: set proxy
    await db.close()


async def reset_posts_status(session: sessionmaker, config: Config):
    db = database(session)
    posts_to_check = await db.post_db.get_posts_status(PostStatusEnum.PLAN_DOWNLOAD)
    posts_to_check += await db.post_db.get_posts_status(PostStatusEnum.LOADING)
    posts_to_check += await db.post_db.get_posts_status(PostStatusEnum.ACTIVE)
    posts_to_check += await db.post_db.get_posts_status(PostStatusEnum.WAIT_PUBLIC)
    posts_to_update_count = 0

    for post in posts_to_check:
        if not post.is_am_downloaded(config):
            await db.post_db.update_post(post.post_id, status=PostStatusEnum.ACTIVE, job_id=None)
            post.delete_me(config)
            posts_to_update_count += 1
        else:
            await db.post_db.update_post(post.post_id, status=PostStatusEnum.PLAN_PUBLIC, job_id=None)

    log.info(f'Пости у кількості {posts_to_update_count} були поновлені у статус Active...')
