import logging
import time

import requests
import sqlalchemy as sa

from app.database.models.base import TimedBaseModel
from app.misc.times import now

log = logging.getLogger(__name__)

class Proxy(TimedBaseModel):

    __tablename__ = 'proxies'

    id = sa.Column(sa.INTEGER, primary_key=True, autoincrement=True, nullable=False)
    function_id = sa.Column(sa.INTEGER, sa.ForeignKey('functions.id', ondelete='SET NULL'), nullable=True)
    host = sa.Column(sa.VARCHAR(100), nullable=False)
    port = sa.Column(sa.VARCHAR(10), nullable=False)
    type = sa.Column(sa.VARCHAR(10), nullable=False, default='socks5')
    login = sa.Column(sa.VARCHAR(100), nullable=True)
    password = sa.Column(sa.VARCHAR(100), nullable=True)
    valid = sa.Column(sa.BOOLEAN, default=False, nullable=False)
    reboot_url = sa.Column(sa.VARCHAR(255), nullable=True)
    last_using_date = sa.Column(sa.DateTime(timezone=True), default=now(), nullable=False)

    def to_dict(self) -> dict:
        if self.login and self.password:
            proxy_url = f'{self.type}://{self.login}:{self.password}@{self.host}:{self.port}'
        else:
            proxy_url = f'{self.type}://{self.host}:{self.port}'
        return {
            'http': proxy_url,
            'https': proxy_url
        }

    def is_proxy_valid(self) -> bool:
        try:
            data = requests.get('https://ipinfo.io/json', proxies=self.to_dict(), timeout=5).json()
            log.info(f'[Проксі працює]: {self.host}:{self.port} {data["timezone"]} - {data["city"]}')
            return True
        except requests.exceptions.ConnectionError:
            log.warning(f'[Проксі НЕ працює]: {self.host}:{self.port}, причина ConnectionError')
            return False
        except requests.exceptions.ReadTimeout:
            log.warning(f'[Проксі НЕ працює]: {self.host}:{self.port}, причина ReadTimeout')
            return False
        except requests.exceptions.InvalidURL:
            log.warning(f'[Проксі НЕ працює]: {self.host}:{self.port}, причина Invalid URL')
            return False
        except:
            log.warning(f'[Проксі НЕ працює]: {self.host}:{self.port}')
            return False

    def reboot_proxy(self) -> bool:
        if self.reboot_url:
            try:
                response = requests.get(self.reboot_url, timeout=10)
                if response.json()['status']:
                    log.warning(f'[Перезагрузка проксі успішна] {self.host}:{self.port}')
                    time.sleep(10)
                return True
            except requests.exceptions.ConnectionError:
                log.error(f'[Перезагрузка проксі НЕ успішна] {self.host}:{self.port}')
                return False
            except requests.exceptions.ContentDecodingError:
                log.error(f'[Перезагрузка проксі НЕ успішна] не зчитана відповідь JSON {self.host}:{self.port}')
                return False
