import json
import time
from datetime import datetime

from sqlalchemy.orm import sessionmaker

from app.instagram.misc import database


async def setup_function_setting(session: sessionmaker):
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

    if await db.proxy_db.count() < 1:
        proxy = await db.proxy_db.add(
            type='socks5', login='FpeKqX9w', password='FpeKqX9w',
            host='v6.getproxy.link', port='32059'
        )
        if proxy.is_proxy_valid():
            await db.proxy_db.update_proxy(proxy.id, valid=False)

        proxy = await db.proxy_db.add(
            type='socks5', login='V75OiLSm', password='V75OiLSm',
            host='v1.getproxy.link', port='32004'
        )

        if proxy.is_proxy_valid():
            await db.proxy_db.update_proxy(proxy.id, valid=False)

        await restore_database_from_json(db)
    await db.close()


async def restore_database_from_json(db: database):

    read = dict(mode='r', encoding='utf-8')
    datetime_format = '%Y-%m-%d %H:%M:%S.%f'

    with open('app/database/users.json', **read) as file:
        data_users = json.load(file)

    for obj in data_users:
        obj: dict
        obj.update(created_at=datetime.strptime(obj['created_at'], datetime_format))
        obj.update(updated_at=datetime.strptime(obj['updated_at'], datetime_format))
        await db.user_db.add(**obj)

    with open('app/database/accounts.json', **read) as file:
        data_accounts = json.load(file)

    data_accounts.sort(key=lambda o: o['account_id'])
    for obj in data_accounts:
        obj: dict
        obj.pop('account_id')
        obj.update(created_at=datetime.strptime(obj['created_at'], datetime_format))
        obj.update(updated_at=datetime.strptime(obj['updated_at'], datetime_format))
        await db.account_db.add(**obj)

    with open('app/database/accounts.json', **read) as file:
        data_accounts_2 = json.load(file)

    with open('app/database/works.json', **read) as file:
        data_works = json.load(file)

    def search(customer_id: int):
        for obj in data_accounts_2:
            if obj['account_id'] == customer_id:
                return obj['username']

    for obj in data_works:
        obj: dict
        obj.pop('work_id')
        obj.update(created_at=datetime.strptime(obj['created_at'], datetime_format))
        obj.update(updated_at=datetime.strptime(obj['updated_at'], datetime_format))
        try:
            obj.update(customer_id=(await db.account_db.get_account_by_username(search(obj['customer_id']))).account_id)
            obj.update(executor_id=(await db.account_db.get_account_by_username(search(obj['executor_id']))).account_id)
            await db.work_db.add(**obj)
        except:
            pass




