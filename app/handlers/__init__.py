import logging

from aiogram import Dispatcher
from aiogram.types import Message, CallbackQuery

from app.config import Config
from app.handlers import error, private, admin
from app.keyboard.inline.menu import help_kb

log = logging.getLogger(__name__)

async def technical_pause_message(msg: Message | CallbackQuery):
    msg = msg if isinstance(msg, Message) else msg.message
    await msg.answer('Бот знаходиться на технічному обслуговуванні. '
                     'Зачекайте будь-ласка та повторіть спробу пізніше', reply_markup=help_kb())

def setup(dp: Dispatcher, config: Config):
    if not config.misc.technical_pause:
        error.setup(dp)
        private.setup(dp)
        admin.setup(dp)
        log.info('Хендлери установлені успішно')
    else:
        dp.register_message_handler(technical_pause_message, state='*')
        dp.register_callback_query_handler(technical_pause_message, state='*')
