import logging

from aiogram import Dispatcher

from app.handlers import error, private, admin
log = logging.getLogger(__name__)


def setup(dp: Dispatcher):
    error.setup(dp)
    private.setup(dp)
    admin.setup(dp)
    log.info('Handlers are successfully configured')
