import concurrent.futures
import logging
from datetime import timedelta, datetime

from apscheduler_di import ContextSchedulerDecorator
from sqlalchemy.orm import sessionmaker

from app.config import Config
from app.database.models import Post, Account, Work
from app.database.services.enums import AccountTypeEnum, AccountStatusEnum, PostStatusEnum, WorkModeEnum, WorkStatusEnum
from app.database.services.repos import PostRepo
from app.instagram.misc import get_post_times, calculate_timeout, database, interval, run_time, \
    concatenate_lists, date
from app.instagram.uploader import InstagramController
from app.misc.times import now, localize

log = logging.getLogger(__name__)
format_time = '%H:%M:%S %d.%m.%y'


async def setup_executors(scheduler: ContextSchedulerDecorator, session: sessionmaker):
    scheduler.add_job(reset_posts_status, **date(10))
    db = database(session)

    ex1 = await db.function_db.get_function('register_posts_executor')
    ex2 = await db.function_db.get_function('manage_posts_executor')
    ex3 = await db.function_db.get_function('public_posts_executor')
    ex4 = await db.function_db.get_function('register_posts_executor_new')
    ex5 = await db.function_db.get_function('check_proxy_executor')

    job1 = scheduler.add_job(register_posts_executor_v2, **interval(**ex1.time))
    job2 = scheduler.add_job(manage_posts_executor_v2, **interval(**ex2.time))
    job3 = scheduler.add_job(public_posts_executor_v3, **interval(**ex3.time))
    job4 = scheduler.add_job(register_posts_executor_new, **interval(**ex4.time))
    job5 = scheduler.add_job(check_proxy_executor, **interval(**ex5.time))
    scheduler.add_job(change_executors_period_function, **interval(minutes=0, delay=30))

    await db.function_db.update_function('register_posts_executor', job_id=job1.id)
    await db.function_db.update_function('manage_posts_executor', job_id=job2.id)
    await db.function_db.update_function('public_posts_executor', job_id=job3.id)
    await db.function_db.update_function('register_posts_executor_new', job_id=job4.id)
    await db.function_db.update_function('check_proxy_executor', job_id=job5.id)


async def change_executors_period_function(session: sessionmaker, scheduler: ContextSchedulerDecorator):
    db = database(session)
    for tag in ['check_proxy_executor', 'register_posts_executor', 'manage_posts_executor',
                'public_posts_executor', 'register_posts_executor_new']:
        me = await db.function_db.get_function(tag)
        if me.job_id:
            if job := scheduler.get_job(me.job_id):
                if me.if_paused_function():
                    job.pause()
                    log.warning(f'[{tag}]: в статусі ПАУЗА')
                else:
                    job.resume()

                scheduler.reschedule_job(job.id, **interval(**me.time, reschedule=True))

async def register_posts_executor_new(session: sessionmaker, scheduler: ContextSchedulerDecorator):
    db = database(session)

    me = await db.function_db.get_function('register_posts_executor_new')
    if me.if_paused_function():
        return

    works = await db.work_db.get_work_mode(WorkModeEnum.ONLY_NEW)
    timeout = 120
    for work in works:
        technicals = await db.account_db.get_free_technicals()
        customer = await db.account_db.get_account(work.customer_id)
        if customer.status not in (AccountStatusEnum.PAUSE, AccountStatusEnum.BANNED):
            technicals.append(customer)
            proxy = db.proxy_db.get_working_proxy(function_id=me.id)
            if not proxy:
                return
            else:
                next_run_time = now() + timedelta(seconds=timeout)
                executor = await db.account_db.get_account(work.executor_id)
                scheduler.add_job(
                    name=f'Регістрація постів для {executor.username}', **run_time(next_run_time),
                    func=run_register_post, kwargs=dict(technicals=technicals, executor=executor, work=work)
                )


async def run_register_post(session: sessionmaker, technicals: list[Account], executor: Account, work: Work,
                            scheduler: ContextSchedulerDecorator):
    db = database(session)
    me = await db.function_db.get_function('register_posts_executor_new')
    proxy = db.proxy_db.get_working_proxy(function_id=me.id)
    if not proxy:
        return
    ex = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    ex.submit(InstagramController(proxy).get_posts, technicals, executor, work, scheduler)


async def register_posts_executor_v2(session: sessionmaker, scheduler: ContextSchedulerDecorator):
    db = database(session)

    me = await db.function_db.get_function('register_posts_executor')
    if me.if_paused_function():
        return

    works = await db.work_db.get_work_mode(WorkModeEnum.LAST_N)
    works += await db.work_db.get_work_mode(WorkModeEnum.ALL)
    works += await db.work_db.get_work_mode(WorkModeEnum.ALL_AND_NEW)

    works.sort(key=lambda w: w.updated_at, reverse=True)

    for work in works:
        technicals = await db.account_db.get_free_technicals()
        customer = await db.account_db.get_account(work.customer_id)
        if customer.status in (AccountStatusEnum.PAUSE, AccountStatusEnum.BANNED):
            pass
        else:
            technicals.append(customer)
            proxy = await db.proxy_db.get_working_proxy(function_id=me.id)
            if not proxy:
                return
            else:
                executor = await db.account_db.get_account(work.executor_id)
                log_msg = f'Перевірка роботи для {customer.username} з {executor.username}'
                log.warning(log_msg)
                ex = concurrent.futures.ThreadPoolExecutor(max_workers=1)
                ex.submit(InstagramController(proxy).get_posts, technicals, executor, work, scheduler)
                return
    await db.close()


async def manage_posts_executor_v2(session: sessionmaker, scheduler: ContextSchedulerDecorator):
    timeout = 50
    db = database(session)

    me = await db.function_db.get_function('manage_posts_executor')
    if me.if_paused_function():
        return

    customers = [customer for customer in await db.account_db.get_accounts_type(AccountTypeEnum.POSTING) if
                 customer.status not in (AccountStatusEnum.PAUSE, AccountStatusEnum.BANNED)]
    sorted_posts = []
    for customer in customers:
        posts = await db.post_db.get_posts_customer(customer.account_id, PostStatusEnum.ACTIVE)
        posts.sort(key=lambda p: p.created_at, reverse=True)
        sorted_posts.append(posts)
    if sorted_posts and now().hour < 23:
        posts = concatenate_lists(*sorted_posts)
        for post in posts:
            customer = await db.account_db.get_account(post.customer_id)
            loading_posts = await db.post_db.get_posts_customer(customer.account_id, PostStatusEnum.LOADING)
            plan_download_posts = await db.post_db.get_posts_customer(customer.account_id, PostStatusEnum.PLAN_DOWNLOAD)
            plan_public_posts = await db.post_db.get_posts_customer(customer.account_id, PostStatusEnum.PLAN_PUBLIC)
            wait_public_posts = await db.post_db.get_posts_customer(customer.account_id, PostStatusEnum.WAIT_PUBLIC)
            counter = sum(len(i) for i in (loading_posts, plan_download_posts, plan_public_posts, wait_public_posts))
            all_plan_download_posts = await db.post_db.get_posts_status(PostStatusEnum.PLAN_DOWNLOAD)
            need_to_download = customer.limit - counter
            if need_to_download > 0:
                log.warning(
                    f'{customer.limit} - {len(loading_posts)} - {len(plan_download_posts)} - {len(plan_public_posts)} '
                    f'- {len(wait_public_posts)} = {need_to_download}'
                )
                times = get_post_times(all_plan_download_posts, scheduler)
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


async def public_posts_executor_v3(session: sessionmaker, scheduler: ContextSchedulerDecorator, config: Config):
    db = database(session)

    me = await db.function_db.get_function('public_posts_executor')
    if me.if_paused_function():
        return

    customers = [customer for customer in await db.account_db.get_accounts_type(AccountTypeEnum.POSTING) if
                 customer.status not in (AccountStatusEnum.PAUSE, AccountStatusEnum.BANNED)]

    def create_stack_list():
        stacks = []
        seconds = (timedelta(days=1) / 50).seconds
        midnight = now().replace(hour=0, minute=0, second=0, microsecond=0)
        for j in range(50):
            stacks.append([midnight + timedelta(seconds=seconds) * j, midnight + timedelta(seconds=seconds) * (j + 1)])
        return stacks

    def get_current_stack_index(date_stack: datetime = None):
        seconds = timedelta(days=1) / 50
        date_stack = localize(date_stack) if date_stack else now()
        return int(timedelta(hours=date_stack.hour, minutes=date_stack.minute,
                             seconds=date_stack.second, microseconds=0) / seconds)

    async def get_waiting_posts_in_stack(stack: list[datetime, datetime], post_db: PostRepo) -> list:
        start, end = stack
        waited_posts = await post_db.get_posts_status(PostStatusEnum.WAIT_PUBLIC)
        post_in_stack = []
        for waited_post in waited_posts:
            if waited_post.job_id and scheduler.get_job(waited_post.job_id):
                if localize(start) <= localize(scheduler.get_job(waited_post.job_id).next_run_time) < localize(end):
                    post_in_stack.append(waited_post)
        return post_in_stack

    def stack_to_string(stack: list[datetime]):
        fmt = '%H:%M:%S'
        return f'{stack[0].strftime(fmt)} - {stack[1].strftime(fmt)}'

    for customer in customers:
        posts = await db.post_db.get_posts_customer(customer.account_id, PostStatusEnum.PLAN_PUBLIC)
        for post in posts:
            wait_public_posts = await db.post_db.get_posts_customer(customer.account_id, PostStatusEnum.WAIT_PUBLIC)
            published_posts = await db.post_db.get_posts_customer(customer.account_id, PostStatusEnum.DONE)
            today_published_posts = [post for post in published_posts
                                     if localize(post.updated_at).strftime('%d.%m.%y') == now().strftime('%d.%m.%y')]
            need_to_public = customer.limit - len(wait_public_posts) - len(today_published_posts)
            # log.warning(
            #     f'{customer.limit} - {len(wait_public_posts)} - {len(today_published_posts)} = {need_to_public}')

            if need_to_public > 0:
                if not post.is_am_downloaded(config) or post.mediacount == 0:
                    post.delete_me(config)
                    await db.post_db.update_post(post.post_id, status=PostStatusEnum.ACTIVE)
                else:
                    for i in range(get_current_stack_index(), 49):
                        next_post_stack = create_stack_list()[i + 1]
                        posts_in_stack = await get_waiting_posts_in_stack(next_post_stack, db.post_db)
                        customer_posts_in_stack = [post for post in posts_in_stack if post.customer_id == customer.account_id]
                        if post not in posts_in_stack and not customer_posts_in_stack and len(posts_in_stack) <= 14:
                            next_run_time = localize(next_post_stack[0] + timedelta(minutes=2) * len(posts_in_stack))
                            public_job = scheduler.add_job(
                                name=f'Публікація поста {post.post_id} в {next_run_time.strftime(format_time)}',
                                **run_time(next_run_time), func=pre_upload_post, kwargs=dict(post=post)
                            )
                            await db.post_db.update_post(post.post_id, status=PostStatusEnum.WAIT_PUBLIC,
                                                         job_id=public_job.id)
                            log_msg = (
                                f'Публікація поста {post.post_id} для {customer.username} заплановано на '
                                f'{next_run_time.strftime(format_time)}'
                            )
                            log.warning(log_msg)
                            break
            else:
                break

    await db.close()


async def public_posts_executor_v2(session: sessionmaker, scheduler: ContextSchedulerDecorator, config: Config):
    db = database(session)
    customers = [customer for customer in await db.account_db.get_accounts_type(AccountTypeEnum.POSTING) if
                 customer.status not in (AccountStatusEnum.PAUSE, AccountStatusEnum.BANNED)]

    sorted_posts = []
    same_customer_limit = 0

    for customer in customers:
        posts = await db.post_db.get_posts_customer(customer.account_id, PostStatusEnum.PLAN_PUBLIC)
        if posts:
            posts.sort(key=lambda p: p.created_at, reverse=True)
            sorted_posts.append(posts)
            same_customer_limit += customer.limit

    if sorted_posts and now().hour < 23:
        posts = concatenate_lists(*sorted_posts)

        for post in posts:
            customer = await db.account_db.get_account(post.customer_id)
            all_wait_public_posts = await db.post_db.get_posts_status(PostStatusEnum.WAIT_PUBLIC)
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
                    times = get_post_times(all_wait_public_posts, scheduler)
                    if not times or max(times) < now():
                        next_run_time = now() + timedelta(seconds=60)
                    else:
                        next_run_time = max(times) + timedelta(seconds=calculate_timeout(same_customer_limit))
                    public_job = scheduler.add_job(
                        name=f'Публікація поста {post.post_id} в {next_run_time.strftime(format_time)}',
                        **run_time(next_run_time), func=pre_upload_post, kwargs=dict(post=post)
                    )
                    await db.post_db.update_post(post.post_id, status=PostStatusEnum.WAIT_PUBLIC, job_id=public_job.id)
                    log_msg = (
                        f'Публікація поста {post.post_id} для {customer.username} заплановано на '
                        f'{next_run_time.strftime(format_time)}'
                    )
                    log.warning(log_msg)
    await db.close()


async def pre_download_post(session: sessionmaker, post: Post, scheduler: ContextSchedulerDecorator):
    db = database(session)
    me = await db.function_db.get_function('manage_posts_executor')
    proxy = await db.proxy_db.get_working_proxy(function_id=me.id)
    customer = await db.account_db.get_account(post.customer_id)
    if customer.status in (AccountStatusEnum.PAUSE, AccountStatusEnum.BANNED):
        await db.post_db.update_post(post.post_id, status=PostStatusEnum.ACTIVE)
        return
    elif not proxy:
        await db.post_db.update_post(post.post_id, status=PostStatusEnum.ACTIVE)
    else:
        technicals = await db.account_db.get_free_technicals()
        technicals.append(customer)
        ex = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        ex.submit(InstagramController(proxy).download_post, technicals, post, scheduler)
        #  TODO: set proxy
    await db.close()


async def pre_upload_post(session: sessionmaker, post: Post, scheduler: ContextSchedulerDecorator):
    db = database(session)
    me = await db.function_db.get_function('public_posts_executor')
    proxy = await db.proxy_db.get_working_proxy(function_id=me.id)
    customer = await db.account_db.get_account(post.customer_id)
    if customer.status in (AccountStatusEnum.PAUSE, AccountStatusEnum.BANNED):
        await db.post_db.update_post(post.post_id, status=PostStatusEnum.PLAN_PUBLIC)
        return
    elif not proxy:
        await db.post_db.update_post(post.post_id, status=PostStatusEnum.PLAN_PUBLIC)
    else:
        ex = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        ex.submit(InstagramController(proxy).upload, customer, post, scheduler)
    await db.close()


async def reset_posts_status(session: sessionmaker, config: Config):
    db = database(session)
    posts_to_check = await db.post_db.get_posts_status(PostStatusEnum.PLAN_DOWNLOAD)
    posts_to_check += await db.post_db.get_posts_status(PostStatusEnum.LOADING)
    posts_to_check += await db.post_db.get_posts_status(PostStatusEnum.ACTIVE)
    posts_to_check += await db.post_db.get_posts_status(PostStatusEnum.WAIT_PUBLIC)
    posts_to_update_count = 0

    for post in posts_to_check:
        customer = await db.account_db.get_account(post.customer_id)
        work = await db.work_db.get_work(post.work_id)
        if not customer or not work:
            post.delete_me(config)
            await db.post_db.delete_post(post.post_id)
        if not post.is_am_downloaded(config):
            await db.post_db.update_post(post.post_id, status=PostStatusEnum.ACTIVE, job_id=None)
            post.delete_me(config)
            posts_to_update_count += 1
        else:
            await db.post_db.update_post(post.post_id, status=PostStatusEnum.PLAN_PUBLIC, job_id=None)

    works = await db.work_db.get_all()
    for work in works:
        if work.mode == WorkModeEnum.ONLY_NEW and work.status == WorkStatusEnum.DONE:
            await db.work_db.update_work(work.work_id, status=WorkStatusEnum.ACTIVE)

    log.info(f'Пости у кількості {posts_to_update_count} були поновлені у статус Active...')


async def update_proxy_status(proxy: int, session: sessionmaker, data: dict):
    db = database(session)
    await db.proxy_db.update_proxy(proxy, **data)
    await db.close()


async def check_proxy_executor(session: sessionmaker, scheduler: ContextSchedulerDecorator):
    db = database(session)

    me = await db.function_db.get_function('check_proxy_executor')
    if me.if_paused_function():
        return

    def check(proxies: list[db.proxy_db.model], session: sessionmaker, scheduler: ContextSchedulerDecorator):
        for proxy in proxies:
            if not proxy.is_proxy_valid():
                data = dict(valid=False)
                scheduler.add_job(name='Оновлення статусу проксі',
                                  func=update_proxy_status, kwargs=dict(proxy=proxy.id, data=data), **date())

    ex = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    # ex.submit(check, await db.proxy_db.get_all(), session, scheduler)
    check(await db.proxy_db.get_all(), session, scheduler)