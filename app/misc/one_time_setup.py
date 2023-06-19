import json
import time
from datetime import datetime

from sqlalchemy.orm import sessionmaker

from app.instagram.misc import database


async def one_time_setup_data(session: sessionmaker, reset_from_json: bool = False):
    db = database(session)
    if await db.function_db.count() < 1:
        await db.function_db.add(
            name='Додавання акаунтів', description='Перевірка чи існує акаунт, який додається',
            minutes=0, seconds=0, tag='add_account'
        )

        await db.function_db.add(
            name='Чекер проксі', description='Перевірка валідності проксі',
            minutes=3, tag='check_proxy_executor'
        )

        await db.function_db.add(
            name='Реєстрація постів', description='Збирання постів з інстаграм',
            minutes=3, tag='register_posts_executor'
        )

        await db.function_db.add(
            name='Скачування постів', description='Планування скачування постів',
            seconds=10, tag='manage_posts_executor'
        )

        await db.function_db.add(
            name='Публікація постів', description='Планування публікації постів',
            seconds=30, tag='public_posts_executor'
        )

        await db.function_db.add(
            name='Регістрація тільки нових постів',
            description='Виконання роботи типу "Тільки нові" та "Нові та всі"',
            minutes=5, tag='register_posts_executor_new'
        )

    if reset_from_json:
        await restore_database_from_json(db)

    await db.close()


async def restore_database_from_function(repo, filename: str, delete: list = None, times: list = None):
    if times is None:
        times = []
    datetime_format = '%Y-%m-%d %H:%M:%S.%f'
    with open(f'app/database/{filename}', mode='r', encoding='utf-8') as file:
        data = json.load(file)
    for obj in data:
        if delete:
            for field in delete:
                obj.pop(field)
        if times:
            for t in times:
                obj.update({t: datetime.strptime(obj[t], datetime_format)})
        obj.update(created_at=datetime.strptime(obj['created_at'], datetime_format))
        obj.update(updated_at=datetime.strptime(obj['updated_at'], datetime_format))
        await repo.add(**obj)

async def restore_database_from_json(db: database):

    await restore_database_from_function(db.user_db, 'users.json')
    await restore_database_from_function(db.account_db, 'accounts.json', delete=['account_id'])
    await restore_database_from_function(db.proxy_db, 'proxies.json', ['id'], ['last_using_date'])




