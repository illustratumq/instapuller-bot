import asyncio
import logging

import betterlogging as bl
from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.redis import RedisStorage2
from aiogram.types import AllowedUpdates, ParseMode

from app import filters, handlers, middlewares
from app.config import Config
from app.database.services.db_engine import create_db_engine_and_session_pool
from app.instagram.executors import setup_executors
from app.instagram.proxy import ProxyController
from app.instagram.uploader import test
from app.misc.bot_commands import set_default_commands
from app.misc.one_time_setup import one_time_setup_data
from app.misc.scheduler import compose_scheduler

# from app.instagram.uploader import test

log = logging.getLogger(__name__)


async def main():
    config = Config.from_env()
    log_level = config.misc.log_level
    bl.basic_colorized_config(level=config.misc.log_level)
    log.info('Starting bot...')

    storage = RedisStorage2(host=config.redis.host, port=config.redis.port)
    bot = Bot(config.bot.token, parse_mode=ParseMode.HTML)
    dp = Dispatcher(bot, storage=storage)
    db_engine, sqlalchemy_session_pool = await create_db_engine_and_session_pool(config.db.sqlalchemy_url, log_level)
    scheduler = compose_scheduler(config, bot, sqlalchemy_session_pool)

    allowed_updates = (
            AllowedUpdates.MESSAGE + AllowedUpdates.CALLBACK_QUERY +
            AllowedUpdates.EDITED_MESSAGE + AllowedUpdates.PRE_CHECKOUT_QUERY +
            AllowedUpdates.SHIPPING_QUERY
    )

    environments = dict(
        config=config,
        scheduler=scheduler,
        controller=ProxyController()
    )

    middlewares.setup(dp, environments, sqlalchemy_session_pool)
    filters.setup(dp)
    handlers.setup(dp)

    await set_default_commands(bot)
    # await one_time_setup_data(sqlalchemy_session_pool, reset_from_json=True)
    await setup_executors(scheduler, sqlalchemy_session_pool)
    # await test(scheduler, sqlalchemy_session_pool, ProxyController())

    try:
        scheduler.start()
        log.info('Scheduler start')
        await dp.skip_updates()
        await dp.start_polling(allowed_updates=allowed_updates, reset_webhook=True)
    finally:
        await storage.close()
        await storage.wait_closed()
        await (await bot.get_session()).close()
        await db_engine.dispose()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.warning('Bot stopped!')
