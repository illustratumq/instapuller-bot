from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import CommandStart
from aiogram.types import Message

from app.config import Config
from app.database.services.repos import UserRepo
from app.keyboard.inline.menu import menu_kb


async def start_cmd(msg: Message, user_db: UserRepo, config: Config, state: FSMContext):
    await state.finish()
    text = (
        '🔄 Instagram Puller Bot\n'
        'Перепублікація та планування постів в Інстаграм\n\n'
        '🗂 Акаунти\n'
        'Список ваших акаунтів. Налаштування, видалення, статистика.\n\n'
        '💸 Підписка\n'
        'Придбати або переглянути підписку'
    )
    greeting_text = (
        '...'
    )
    user = await user_db.get_user(msg.from_user.id)
    if not user and not msg.from_user.is_bot:
        await user_db.add(
            user_id=msg.from_user.id,
            mention=msg.from_user.get_mention(),
            full_name=msg.from_user.full_name
        )
        await msg.answer(greeting_text, disable_web_page_preview=True)
    admin = msg.from_user.id in config.bot.admin_ids or msg.from_user.is_bot
    await msg.answer(text, reply_markup=menu_kb(admin))


def setup(dp: Dispatcher):
    dp.register_message_handler(start_cmd, CommandStart(), state='*')


