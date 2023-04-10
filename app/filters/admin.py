from aiogram.dispatcher.filters import BoundFilter
from aiogram.dispatcher.handler import ctx_data
from aiogram.types import Message, CallbackQuery

from app.config import Config


class IsAdminFilter(BoundFilter):
    async def check(self, upd: Message | CallbackQuery, *args: ...) -> bool:
        data: dict = ctx_data.get()
        config: Config = data['config']
        return upd.from_user.id in config.bot.admin_ids
