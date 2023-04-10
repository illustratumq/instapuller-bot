from datetime import datetime

import pytz

from app.config import Config

config = Config.from_env()


def now():
    return datetime.now().astimezone(pytz.timezone(config.misc.timezone))


def localize(date: datetime):
    return date.astimezone(pytz.timezone(config.misc.timezone))