from aiogram import Dispatcher

from app.handlers.admin import statistic, admin


def setup(dp: Dispatcher):
    statistic.setup(dp)
    admin.setup(dp)