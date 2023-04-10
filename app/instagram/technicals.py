import logging

from sqlalchemy.orm import sessionmaker

from app.database.services.enums import AccountTypeEnum
from app.instagram.misc import JsonWrapper
from app.instagram.misc import database

log = logging.getLogger(__name__)


class TechnicalOneSetup:

    writer = JsonWrapper('app/instagram/technicals.json')

    @staticmethod
    def get_technicals() -> list[dict]:
        return TechnicalOneSetup.writer.list()

    @staticmethod
    def write_technicals(account: str):
        account_string = account.replace(' ', '')
        username, password, key2fa = account_string.split(';')
        if TechnicalOneSetup.writer.get(username) is not None:
            return
        TechnicalOneSetup.writer.append(
            {
                username: dict(
                    username=username,
                    password=password,
                    key2fa=key2fa,
                )
            }
        )

    @staticmethod
    async def add_accounts_to_db(session: sessionmaker):
        db = database(session)
        log.info('Встановалюю технічні акаунти...')
        for account in TechnicalOneSetup.writer.list():
            account_data = TechnicalOneSetup.writer.get(account)
            username = account_data['username']
            password = account_data['password']
            key2fa = account_data['key2fa']
            account_in_database = await db.account_db.get_account_by_username(username, AccountTypeEnum.TECHNICAL)
            if account_in_database is None:
                await db.account_db.add(
                    username=username, password=password, auth_key=key2fa, type=AccountTypeEnum.TECHNICAL
                )
                log.info(f'{username} додано в базу даних...')
        await db.close()
