from .base import *


class ParsingSG(StatesGroup):
    Type = State()
    Login = State()
    Password = State()
    Confirm = State()
    Check = State()


class PostingSG(StatesGroup):
    Type = State()
    Login = State()
    Password = State()
    Confirm = State()
    Check = State()


class LastNSG(StatesGroup):
    Input = State()


class InstagramDataSG(StatesGroup):
    Input = State()
