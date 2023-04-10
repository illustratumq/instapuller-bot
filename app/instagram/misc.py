import json
import os
from datetime import timedelta, datetime

from aiogram import Bot
from aiogram.types import InputFile
from apscheduler_di import ContextSchedulerDecorator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import Config
from app.database.models import Account, Post, Work
from app.database.services.repos import *
from app.misc.times import localize, now


def date(seconds: int = 5):
    return dict(trigger='date', next_run_time=now() + timedelta(seconds=seconds), misfire_grace_time=300)


def run_time(next_run_time: datetime):
    return dict(trigger='date', next_run_time=next_run_time, misfire_grace_time=300)


def interval(delay: int = 0, minutes: float = 0):
    return dict(trigger='interval', seconds=int(minutes*60+delay), max_instances=2, misfire_grace_time=300)


class database:
    def __init__(self, session: sessionmaker):
        self.session: AsyncSession = session() if isinstance(session, sessionmaker) else session

    @property
    def account_db(self) -> AccountRepo:
        return AccountRepo(self.session)

    @property
    def post_db(self) -> PostRepo:
        return PostRepo(self.session)

    @property
    def work_db(self) -> WorkRepo:
        return WorkRepo(self.session)

    @property
    def user_db(self) -> UserRepo:
        return UserRepo(self.session)

    async def close(self):
        await self.session.commit()
        await self.session.close()


class JsonWrapper:

    def __init__(self, path: str):
        self.path = path

    @property
    def read(self):
        return dict(file=self.path, mode='r', encoding='utf-8')

    @property
    def write(self):
        return dict(file=self.path, mode='w', encoding='utf-8')

    def append(self, new_data: dict):
        with open(**self.read) as file:
            data = dict(json.load(file))
        data.update(new_data)
        with open(**self.write) as file:
            json.dump(data, file, indent=4)

    def delete(self, item: str):
        items = self.list()
        new_data = {}
        for key in items:
            if key != item:
                new_data.update({key: self.get(key)})
        with open(**self.write) as file:
            json.dump(new_data, file, indent=4)

    def get(self, item: str) -> dict:
        with open(**self.read) as file:
            return dict(json.load(file)).get(item)

    def list(self):
        with open(**self.read) as file:
            return [obj for obj in json.load(file)]


def get_post_times(posts: list[Post], scheduler: ContextSchedulerDecorator):
    times = []
    for post in posts:
        if post.job_id and scheduler.get_job(post.job_id):
            times.append(localize(scheduler.get_job(post.job_id).next_run_time))
    return times


def calculate_timeout(limit: int):
    midnight = (now() + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    seconds_to_midnight = (midnight - now()).seconds
    return int(seconds_to_midnight/limit)


def concatenate_lists(*lists):
    max_length = max(len(lst) for lst in lists)
    concatenated_list = []
    for i in range(max_length):
        for lst in lists:
            if i < len(lst):
                concatenated_list.append(lst[i])
    return concatenated_list


def list_post_files(post_id: str, config: Config):
    post_path = f'{config.misc.download_path}/{post_id}/'
    files = [f'{config.misc.download_path}/{post_id}/{file}' for file in os.listdir(post_path)
             if file.startswith('file')]
    files.sort(key=lambda s: int(s.split('.')[0].split('_')[-1]))
    return files


def run_func_timeout(seconds: int = 5) -> dict:
    return dict(
        trigger='date', next_run_time=now() + timedelta(seconds=seconds), max_instances=3,
        misfire_grace_time=60
    )


async def send_message(bot: Bot, user_id: int | list, text: str, screenshot: str):
    if screenshot and screenshot.split('/')[-1] in os.listdir('app/instagram/screenshots/'):
        if isinstance(user_id, list):
            for usr_id in user_id:
                await bot.send_photo(usr_id, photo=InputFile(screenshot), caption=text)
        else:
            await bot.send_photo(user_id, photo=InputFile(screenshot), caption=text)
        os.remove(screenshot)
    else:
        if isinstance(user_id, list):
            for usr_id in user_id:
                await bot.send_message(usr_id, text=text)
        else:
            await bot.send_message(user_id, text=text)


async def update_account(session: sessionmaker, account: Account, params: dict):
    db = database(session)
    await db.account_db.update_account(account.account_id, **params)
    await db.close()


async def update_work(session: sessionmaker, work: Work, params: dict):
    db = database(session)
    await db.work_db.update_work(work.work_id, **params)
    await db.close()


async def add_posts(session: sessionmaker, work: Work, shortcodes: list[str]):
    db = database(session)
    for post_id in shortcodes:
        if not await db.post_db.if_post_exist(work.customer_id, post_id):
            await db.post_db.add(
                post_id=post_id,
                user_id=work.user_id,
                customer_id=work.customer_id,
                executor_id=work.executor_id,
                work_id=work.work_id
            )
    media_count = len(await db.post_db.get_post_work(work.work_id))
    await db.work_db.update_work(work.work_id, mediacount=media_count)


async def update_post(session: sessionmaker, post: Post, params: dict):
    db = database(session)
    await db.post_db.update_post(post.post_id, **params)
    await db.close()


async def delete_post(session: sessionmaker, post: Post):
    db = database(session)
    config = Config.from_env()
    post.delete_me(config)
    await db.post_db.delete_post(post.post_id)
    await db.close()
