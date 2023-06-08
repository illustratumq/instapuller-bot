import logging
import time
from datetime import datetime

import requests
from babel.dates import format_datetime

from app.instagram.misc import JsonWrapper
from app.misc.times import now, localize
import subprocess
import platform

log = logging.getLogger(__name__)


def ping(host):
    ping_str = "-n 1" if platform.system().lower() == "windows" else "-c 1"
    args = "ping " + " " + ping_str + " " + host
    need_sh = False if platform.system().lower() == "windows" else True
    return subprocess.call(args, shell=need_sh) == 0


class ProxyController:

    writer = JsonWrapper('app/instagram/proxy.json')

    @staticmethod
    def proxy_statistic():
        answer = ''
        writer = JsonWrapper('app/instagram/proxy.json')
        proxy_list = writer.list()
        proxy_list.sort(key=lambda k: writer.get(k)['status'], reverse=True)
        for key, count in zip(proxy_list, range(1, len(proxy_list) + 1)):
            proxy_data = writer.get(key)
            last_using = format_datetime(
                localize(datetime.fromtimestamp(proxy_data['update_date'])),
                locale='uk_UA', format='medium'
            )
            status = proxy_data['status']
            marker = '🟢' if status == 'ok' else '🟠'
            answer += f'{count}.  {marker} <code>{key}</code> {last_using}\n'
        return answer

    @staticmethod
    def get_working_proxy(executor_type: str = 'default'):
        worked_proxies = []
        writer = JsonWrapper('app/instagram/proxy.json')
        for proxy in writer.list():
            worked_proxies.append(writer.get(proxy))
        worked_proxies.sort(key=lambda data: now().fromtimestamp(data['last_using']))
        for proxy_data in worked_proxies:
            status = proxy_data['status']
            proxy_string = proxy_data['proxy_string']
            type_ = proxy_data['type']
            host, port, proxy_type, reboot_url = proxy_string.split(';')
            if status == 'ok':
                if executor_type == 'default':
                    key = f'{host};{port}'
                    if not ProxyController.check_proxy(proxy_string):
                        ProxyController.update(key, status='not valid', stop_time=now().timestamp())
                        log.warning(proxy_string + ' not valid')
                    else:
                        return proxy_string
                else:
                    if type_ == executor_type:
                        key = f'{host};{port}'
                        if not ProxyController.check_proxy(proxy_string):
                            ProxyController.update(key, status='not valid', stop_time=now().timestamp())
                            log.warning(proxy_string + ' not valid')
                        else:
                            return proxy_string

    @staticmethod
    def recheck_proxies():
        writer = ProxyController.writer
        for proxy in writer.list():
            proxy_data = writer.get(proxy)
            proxy_string = proxy_data['proxy_string']
            total_actions = int(proxy_data['total_actions'])
            if ProxyController.check_proxy(proxy_string):
                log.warning(f'{proxy} is ok')
                ProxyController.update(proxy, status='ok', free_actions=total_actions)
            else:
                log.warning(f'{proxy} not valid')
                ProxyController.update(proxy, status='not valid', stop_time=now().timestamp())

    @staticmethod
    def use_proxy(proxy_string: str):
        host, port, proxy_type, url = proxy_string.split(';')
        key = f'{host};{port}'
        proxy_data = ProxyController.writer.get(key)
        free_actions = int(proxy_data['free_actions'])
        if free_actions == 0:
            total_actions = int(proxy_data['total_actions'])
            free_actions = total_actions
        else:
            free_actions -= 1
        ProxyController.update(
            key, free_actions=free_actions, last_using=now().timestamp(),
        )

    @staticmethod
    def reboot_proxy(proxy_string: str):
        host, port, proxy_type, reboot_url = proxy_string.split(';')
        key = f'{host};{port}'
        try:
            response = requests.get(reboot_url, timeout=10)
            if response.json()['status']:
                log.warning(f'Reboot proxy {key} status ok')
                time.sleep(10)
                ProxyController.update(key)
        except requests.exceptions.ConnectionError:
            log.error(f'Reboot proxy {key} status: bad')
            return False
        except requests.exceptions.ContentDecodingError:
            log.error('Помилка при зчитуванні відповіді JSON')

    @staticmethod
    def check_proxy(proxy_string: str):
        host, port, proxy_type, reboot_url = proxy_string.split(';')
        try:
            proxy_url = f'{proxy_type}://{host}:{port}'
            proxies = dict(http=proxy_url, https=proxy_url)
            data = requests.get('https://ipinfo.io/json', proxies=proxies, timeout=5)
            return True
        except requests.exceptions.ConnectionError:
            return False
        except requests.exceptions.InvalidURL:
            log.warning(f'Invalid URL with {host}:{port}')
            return False

    @staticmethod
    def update(key: str, **values):
        proxy = ProxyController.writer.get(key)
        proxy.update(**values, update_date=now().timestamp())
        ProxyController.writer.append({key: proxy})

    @staticmethod
    def write_proxy(proxy_string: str):
        proxy_string = proxy_string.replace(' ', '')
        host, port, proxy_type, reboot_url = proxy_string.split(';')
        status = 'ok' if ProxyController.check_proxy(proxy_string) else 'not valid'
        create_date = now().timestamp()
        ProxyController.writer.append(
            {
                f'{host};{port}': dict(
                    proxy_string=proxy_string,
                    status=status,
                    create_date=create_date,
                    update_date=create_date,
                    last_using=create_date,
                    free_actions=10,
                    total_actions=10
                )
            }
        )

