from typing import Any

from aiogram.dispatcher.middlewares import LifetimeControllerMiddleware
from aiogram.types.base import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.database.services.repos import *


class DatabaseMiddleware(LifetimeControllerMiddleware):
    skip_patterns = ['error', 'update']

    def __init__(self, session_pool: sessionmaker) -> None:
        self.session_pool = session_pool
        super().__init__()

    async def pre_process(self, obj: TelegramObject, data: dict, *args: Any) -> None:
        session: AsyncSession = self.session_pool()
        data['user_db'] = UserRepo(session)
        data['work_db'] = WorkRepo(session)
        data['account_db'] = AccountRepo(session)
        data['post_db'] = PostRepo(session)
        data['proxy_db'] = ProxyRepo(session)
        data['function_db'] = FunctionRepo(session)
        data['error_db'] = ErrorRepo(session)
        data['session_pool'] = self.session_pool
        data['session'] = session

    async def post_process(self, obj: TelegramObject, data: dict, *args: Any) -> None:
        if session := data.get('session', None):
            session: AsyncSession
            await session.close()
