from .base import *


class ModeSG(StatesGroup):
    Input = State()


class PerdaySG(StatesGroup):
    Input = State()


class ProxySG(StatesGroup):
    Input = State()


class FileSG(StatesGroup):
    InputAccounts = State()
    InputProxies = State()
    InputDeleteProxy = State()


class ApproveSG(StatesGroup):
    Input = State()


class AuthSG(StatesGroup):
    Input = State()


class AdminSG(StatesGroup):
    Text = State()