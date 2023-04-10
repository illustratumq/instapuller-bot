import logging
from typing import Any

from aiogram import Dispatcher
from sqlalchemy.orm import sessionmaker

from app.middlewares.database import DatabaseMiddleware
from app.middlewares.environment import EnvironmentMiddleware
from app.middlewares.throttling import ThrottlingMiddleware

log = logging.getLogger(__name__)


def setup(dp: Dispatcher, environments: dict[str, Any], session_pool: sessionmaker):
    dp.setup_middleware(EnvironmentMiddleware(environments))
    dp.setup_middleware(DatabaseMiddleware(session_pool))
    log.info('Middlewares are successfully configured')
