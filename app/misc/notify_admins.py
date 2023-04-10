import logging

from aiogram import Bot

log = logging.getLogger(__name__)


async def notify(bot: Bot, config) -> None:
    if config.misc.notify_admin:
        for admin in config.bot.admin_ids:
            try:
                await bot.send_message(admin, 'Бот запущено')
            except Exception as err:
                log.exception(err)
