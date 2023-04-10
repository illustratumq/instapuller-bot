from aiogram import Bot
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.executors.base import BaseExecutor
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler_di import ContextSchedulerDecorator
from sqlalchemy.orm import sessionmaker
from tzlocal import get_localzone

from app.config import Config


def _configure_executors() -> dict[str, BaseExecutor]:
    return {
        'threadpool': ThreadPoolExecutor(),
        'default': AsyncIOExecutor()
    }


def compose_scheduler(config: Config, bot: Bot, session: sessionmaker) -> ContextSchedulerDecorator:
    scheduler = ContextSchedulerDecorator(AsyncIOScheduler(
        executors=_configure_executors(),
        timezone=str(get_localzone())
    ))
    scheduler.ctx.add_instance(bot, Bot)
    scheduler.ctx.add_instance(session, sessionmaker)
    scheduler.ctx.add_instance(config, Config)
    scheduler.ctx.add_instance(scheduler, ContextSchedulerDecorator)
    return scheduler
