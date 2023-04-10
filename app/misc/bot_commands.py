from aiogram import types, Bot
import logging


async def set_default_commands(bot: Bot):
    await bot.set_my_commands(
        [
            types.BotCommand('start', '[Ре]Старт боту'),
            # types.BotCommand('admin', 'Панель адміністратора')
        ]
    )
    logging.info("Установка комманд пройшла успішно")
