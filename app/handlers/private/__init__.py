from aiogram import Dispatcher

from . import start
from . import menu
from . import back
from . import add
from . import posting
from . import parsing
from . import statistic


def setup(dp: Dispatcher):
    back.setup(dp)
    start.setup(dp)
    menu.setup(dp)
    add.setup(dp)
    posting.setup(dp)
    parsing.setup(dp)
    statistic.setup(dp)


