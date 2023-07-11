import json
import logging
import os
import pickle
import platform
import socket
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pyotp
import requests
from apscheduler_di import ContextSchedulerDecorator
from bs4 import BeautifulSoup, NavigableString
from selenium.common import WebDriverException, NoSuchElementException
from selenium.webdriver import Keys, ActionChains
from seleniumwire import webdriver
from sqlalchemy.orm import sessionmaker
from telebot import TeleBot
from telebot.types import InputFile

from app.config import Config
from app.database.models import Account, Proxy
from app.database.models import Work, Post
from app.database.services.enums import WorkModeEnum, WorkStatusEnum, PostStatusEnum, AccountTypeEnum, AccountStatusEnum
from app.instagram.misc import date, update_account, create_error
from app.instagram.misc import send_message, update_work, add_posts, delete_post, update_post
from app.instagram.proxy import ProxyController
from app.misc.times import now

log = logging.getLogger(__name__)
logging.getLogger('seleniumwire').setLevel(logging.ERROR)


class Device:
    SERVER = 'SERVER'
    WINDOWS = 'WINDOWS'

    @staticmethod
    def current():
        return Device.WINDOWS if platform.system().lower() == 'windows' else Device.SERVER


@dataclass
class Button:
    entry: tuple = 'xpath', '//*[@id="loginForm"]/div/div[3]/button'
    accept_cookies: tuple = 'xpath', '//button[contains(text(), "Not Now")]'
    select_file: tuple = 'xpath', "//*[contains(text(), 'Select from computer')]"
    input: tuple = 'tag name', 'input'
    next: tuple = 'xpath', '//button[contains(text(), "Next")]'
    share: tuple = 'xpath', '//button[contains(text(), "Share")]'
    security: tuple = 'css selector', "[aria-label='Security Code']"
    confirm: tuple = 'xpath', "//*[contains(text(), 'Confirm')]"
    post_count: tuple = 'class name', '_ac2a'
    create = 'xpath', "//*[contains(text(), 'Create')]"
    error: tuple = 'xpath', '//*[@id="slfErrorAlert"]'
    scroll: str = 'window.scrollTo(0, document.body.scrollHeight);'
    query_hash: str = '2b0673e0dc4580674a88d426fe00ea90'
    images = {'name': 'div', 'class_': '_aagu _aato'}
    images_closed = {'name': 'div', 'class_': '_aagu _aa20 _aato'}
    image = {'name': 'div', 'class_': '_aagv'}
    videos = {'name': 'div', 'class_': '_ab1c'}


class ErrorLoginInstagram(Exception):
    pass


class InstagramController:

    login_url = 'https://www.instagram.com'
    post_url = 'https://www.instagram.com/p/{}'
    profile_url = 'https://www.instagram.com/{}'
    graphql_url = 'https://www.instagram.com/graphql/query'

    screen_path = 'app/instagram/screenshots/{}_{}.png'
    download_path = 'app/instagram/download/'
    cookies_path = 'app/instagram/cookies/'

    cookies_form = '{}_cookies.pkl'
    format_time = '%H%M%S'

    def __init__(self, proxy: Proxy = None):
        self.config = Config.from_env()
        self.proxy: Proxy = proxy
        self.browser: webdriver.Chrome = None
        self.button = Button

    def set_browser(self):
        if Device.current() == Device.WINDOWS:
            self.browser = webdriver.Chrome(**self.windows_options(), executable_path='../../chromedriver.exe')
            log.info('Відкриваю Chrome на Windows...')
            time.sleep(1)
            self.browser.get('https://ipinfo.io/json')
            time.sleep(1)
            self.browser.refresh()
        else:
            for port in range(4, 9):
                try:
                    self.browser = webdriver.Remote(command_executor=f'http://selenoid:444{port}/wd/hub',
                                                    **self.options(port))
                    time.sleep(3)
                    self.browser.get('https://ipinfo.io/jsonhttps://ipinfo.io/json')
                    self.browser.save_screenshot('view.png')
                    bot = TeleBot(self.config.bot.token)
                    bot.send_photo(454793780, InputFile('view.png'))
                    time.sleep(1)
                    break
                except Exception as err:
                    log.error(f'\nНе зміг підключитись до порту: 444{port}\n\n{err}\n')

    def windows_options(self, **kwargs) -> dict:
        options = webdriver.ChromeOptions()
        options.add_argument("--lang=eng")
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--ignore-ssl-errors=yes')
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        options.add_experimental_option('excludeSwitches', ['enable-automation'])

        desired_capabilities = {
            'browserName': 'chrome',
            'version': 'latest',
            'platform': 'WINDOWS',
        }

        result = dict(options=options, desired_capabilities=desired_capabilities)

        if self.proxy:
            self.proxy.reboot_proxy()
            wire_options = dict(proxy=self.proxy.to_dict())
            result.update(seleniumwire_options=wire_options)

        return result

    @property
    def container_local_ip(self) -> str:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        for addr, port in zip(['selenoid', 'selenoid', '0.0.0.0', '0.0.0.0'], [80, 4444, 80, 4444]):
            try:
                s.connect(('8.8.8.8', 80))
                address = s.getsockname()[0]
                log.warning(f'{addr} - {address}')
            except:
                log.error(f'{addr} fail')
        s.connect(('8.8.8.8', 80))
        address = s.getsockname()[0]
        return address

    def options(self, port: int) -> dict:
        options = webdriver.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument("--lang=eng")
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--ignore-ssl-errors=yes')
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        options.add_experimental_option('excludeSwitches', ['enable-automation'])

        desired_capabilities = {
            'browserName': 'chrome',
            'version': 'latest',
            'platform': 'LINUX',
            'acceptSslCerts': True,
            'selenoid:options': {
                'enableVNC': True
            }
        }

        result = dict(options=options, desired_capabilities=desired_capabilities)

        wire_options = {
            'connection_timeout': None,
            'addr': self.container_local_ip,
            'port': 4440 + port
        }

        if self.proxy:
            self.proxy.reboot_proxy()
            wire_options.update(proxy=self.proxy.to_dict())

        result.update(seleniumwire_options=wire_options)

        return result

    @staticmethod
    def error_to_html(error: Exception):
        return str(error).replace('<', '').replace('>', '')

    def is_exist(self, *args) -> bool:
        try:
            self.browser.find_element(*args)
            exist = True
        except NoSuchElementException:
            exist = False
        return exist

    def click(self, *args, browser: webdriver.Chrome, check_exist: bool = False):
        if check_exist:
            if not self.is_exist(*args):
                return
        browser.execute_script('arguments[0].click();', browser.find_element(*args))

    @staticmethod
    def get_button(browser: webdriver.Chrome, name: str):
        buttons = browser.find_elements('tag name', 'button')
        for b in buttons:
            try:
                if b.accessible_name == name:
                    return b
            except WebDriverException:
                pass

    def is_cookies_exist(self, login: str):
        return self.cookies_form.format(login) in os.listdir(self.cookies_path)

    def confirmations(self, browser: webdriver.Chrome):
        self.click(*self.button.accept_cookies, browser=browser, check_exist=True)

    def get_cookies(self, browser: webdriver.Chrome, login: str) -> None:
        log.info(f'Load cookies for {login}')
        try:
            with open(Path(self.cookies_path, self.cookies_form.format(login)), 'rb') as file:
                cookies = pickle.load(file)
                browser.delete_all_cookies()
                for cookie in cookies:
                    browser.add_cookie(cookie)
                browser.refresh()
            time.sleep(5)
            self.confirmations(browser)
        except:
            log.warning(f'Bad cookies set to {login}')

    def save_cookies(self, browser: webdriver.Chrome, login: str):
        log.info(f'Save cookies for {login}')
        with open(Path(self.cookies_path, self.cookies_form.format(login)), mode='wb') as file:
            pickle.dump(browser.get_cookies(), file)

    @staticmethod
    def is_page_not_available(browser: webdriver.Chrome):
        return 'Sorry, this page isn\'t available.' in browser.page_source

    @staticmethod
    def is_video_exist(soup: BeautifulSoup) -> bool:
        return len(soup.find_all('div', class_='_ab1c')) + len(soup.find_all('video')) > 0

    @staticmethod
    def get_auth_keycode(key: str):
        for i in range(2):
            code = pyotp.TOTP(key.replace(' ', ''))
            time_remaining = int(code.interval - datetime.now().timestamp() % code.interval)
            if time_remaining >= 5:
                return code.now()
            else:
                time.sleep(6)

    @staticmethod
    def count_page_elements(browser: webdriver.Chrome, name: str, tag: str, text: bool = False):
        buttons = browser.find_elements('tag name', tag)
        count = 0
        for b in buttons:
            try:
                if text:
                    if name == str(b.text):
                        count += 1
                else:
                    if name in b.accessible_name:
                        count += 1
            except WebDriverException:
                pass
        return count

    @staticmethod
    def get_element_by_name(browser: webdriver.Chrome, name: str, tag: str, text: bool = False,
                            reverse: bool = False):
        buttons = browser.find_elements('tag name', tag)
        if reverse:
            buttons = buttons[::-1]
        for b in buttons:
            try:
                if text:
                    if name == str(b.text):
                        return b
                else:
                    if name in b.accessible_name:
                        return b
            except WebDriverException:
                pass

    def login(self, account: Account, scheduler: ContextSchedulerDecorator,
              successful_end_func=None, error_end_func=None, kwargs: dict = None) -> webdriver.Chrome:
        screenshot = self.screen_path.format(account.username, now().strftime(self.format_time))
        try:
            for attempt in (1, 2):
                log.info(f'Логін в {account.username}. Спроба {attempt}/2')
                self.set_browser()
                browser: webdriver.Chrome = self.browser
                browser.get(self.login_url)
                time.sleep(3)
                browser.implicitly_wait(30)
                browser.save_screenshot(screenshot)
                allow_cookies = self.get_button(browser, 'Allow essential and optional cookies')
                if allow_cookies:
                    browser.execute_script('arguments[0].click();', allow_cookies)
                if self.is_cookies_exist(account.username):
                    self.get_cookies(browser, account.username)
                    browser.save_screenshot(screenshot)
                    time.sleep(5)
                    browser.implicitly_wait(30)
                    if not self.is_exist(*self.button.create) and self.get_button(browser, 'New post') is None:
                        pass
                    else:
                        if os.path.isfile(screenshot):
                            os.remove(screenshot)
                        if successful_end_func:
                            scheduler.add_job(successful_end_func, **date(), kwargs=kwargs)
                        return browser
                self.get_element_by_name(browser, 'Phone number, username', tag='input').send_keys(account.username)
                time.sleep(1)
                self.get_element_by_name(browser, 'Password', tag='input').send_keys(account.password)
                time.sleep(1)
                self.get_button(browser, 'Log in').send_keys(Keys.ENTER)
                time.sleep(5)
                browser.implicitly_wait(30)
                browser.save_screenshot(screenshot)
                if self.is_exist(*self.button.error):
                    error = browser.find_element(*self.button.error).text
                    raise ErrorLoginInstagram(error)
                if account.auth_key:
                    button = browser.find_element(*self.button.security)
                    if button is not None:
                        button.send_keys(self.get_auth_keycode(account.auth_key))
                        self.click(*self.button.confirm, browser=browser)
                        time.sleep(5)
                        if not self.is_exist(*self.button.create) and self.get_button(browser, 'New post') is None:
                            raise ErrorLoginInstagram('Бот не зміг увійти в ваш акаунт. Схоже ваш код двоетапної '
                                                      'перевірки некоректний')
                browser.save_screenshot(screenshot)
                post_blocked = self.get_button(browser, 'OK')
                if post_blocked:
                    post_blocked.send_keys(Keys.ENTER)
                    time.sleep(2)
                self.confirmations(browser)
                time.sleep(2)
                if not self.is_exist(*self.button.create) and self.get_button(browser, 'New post') is None:
                    raise ErrorLoginInstagram('Бот не зміг увійти в ваш акаунт.')
                self.save_cookies(browser, account.username)
                log.info(f'Successfully login for {account.username}')
                os.remove(screenshot)
                if successful_end_func:
                    scheduler.add_job(successful_end_func, **date(), kwargs=kwargs)
                return browser
        except Exception as Error:
            self.close(self.browser)
            error = self.error_to_html(Error)
            if 'session timed out or not found' in error:
                pass
            else:
                text = (
                    f'#ПомилкаВходуІнстаграм\n\n'
                    f'Я не зміг увійтив ваш акаунт <b>{account.username}</b>\n\n<code>{error}</code>'
                )
                if account.type == AccountTypeEnum.TECHNICAL:
                    user_id = self.config.misc.error_channel_id
                else:
                    user_id = [account.user_id, self.config.misc.error_channel_id]

                error_data = dict(
                    name='Помилка при вході в акаунт',
                    description=f'Функція login\n\n{error}', customer_id=account.account_id,
                    proxy_id=self.proxy.id, screenshot=screenshot
                )

                scheduler.add_job(
                    name=f'Відправка повідомлення про помилку при вході в {account.username}',
                    func=send_message, **date(), kwargs=dict(user_id=user_id, text=text, screenshot=screenshot)
                )
                scheduler.add_job(
                    name=f'Оновлення статусту акаунту на "Забанений"', func=update_account, **date(7),
                    kwargs=dict(account=account, params=dict(status=AccountStatusEnum.BANNED))
                )
                scheduler.add_job(
                    name='Створення обєкту помилки', func=create_error, **date(9),
                    kwargs=dict(data=error_data)
                )
                if error_end_func:
                    scheduler.add_job(error_end_func, **date(10), kwargs=kwargs)

    def check_parsing_account(self, technicals: list[Account], username: str, scheduler: ContextSchedulerDecorator,
                              successful_end_func=None, error_end_func=None, kwargs: dict = None):
        for technical in technicals:
            browser = self.login(technical, scheduler)
            if browser:
                browser.get(self.profile_url.format(username))
                time.sleep(5)
                if self.get_element_by_name(browser, 'Sorry, this page isn\'t available.', tag='h2'):
                    scheduler.add_job(error_end_func, **date(), kwargs=kwargs)
                elif not self.get_element_by_name(browser, username, tag='h2', text=True):
                    scheduler.add_job(error_end_func, **date(), kwargs=kwargs)
                else:
                    scheduler.add_job(successful_end_func, **date(), kwargs=kwargs)
                browser.close()
                return
            else:
                pass
        scheduler.add_job(error_end_func, **date(), kwargs=kwargs)
        text = f'Не зміг перевірити на дійсність акаунт {username}, використано {len(technicals)} спроб'
        scheduler.add_job(
            send_message, **date(), kwargs=dict(user_id=self.config.misc.error_channel_id, text=text, screenshot='None')
        )

    def get_posts(self, technicals: list[Account],  executor: Account, work: Work,
                  scheduler: ContextSchedulerDecorator):
        for technical in technicals:
            screenshot = self.screen_path.format(technical.username, now().strftime(self.format_time))
            browser = self.login(technical, scheduler)
            if browser:
                try:
                    browser.get(self.profile_url.format(executor.username))
                    time.sleep(5)
                    browser.implicitly_wait(5)
                    try:
                        current_media_count = int(browser.find_elements(
                            *self.button.post_count)[0].text.replace(',', ''))
                    except IndexError:
                        error_msg = (
                            f'Не можливо спарсити к-ть медія на сторінці акаунту. Перевірте '
                            f'чи він існує в Інстаграм.'
                        )
                        raise ErrorLoginInstagram(error_msg)
                    browser.save_screenshot(screenshot)

                    limit = 0
                    update_work_kwargs = dict(status=WorkStatusEnum.DONE, mediacount=current_media_count)
                    if work.mode == WorkModeEnum.ALL:
                        limit = current_media_count
                    elif work.mode == WorkModeEnum.LAST_N:
                        limit = work.limit
                    elif work.mode == WorkModeEnum.ONLY_NEW:
                        update_work_kwargs.update(status=WorkStatusEnum.ACTIVE)
                        if work.mediacount != 0 and current_media_count > work.mediacount:
                            limit = current_media_count - work.mediacount
                            update_work_kwargs.update(mediacount=current_media_count)
                        else:
                            browser.close()
                            return
                    elif work.mode == WorkModeEnum.ALL_AND_NEW:
                        update_work_kwargs.update(mediacount=current_media_count, status=WorkStatusEnum.ACTIVE,
                                                  mode=WorkModeEnum.ONLY_NEW)
                        limit = current_media_count

                    page_load_attempt = 0
                    caught_posts = []
                    pinned_posts = self.count_page_elements(browser, 'Pinned post icon', 'svg')
                    while len(caught_posts) < limit:
                        try:
                            pinned_post_index = pinned_posts if not caught_posts else 0
                            elements = browser.find_elements('tag name', 'a')
                            cache = [link.get_attribute('href').split('/')[-2]
                                     for link in elements if '/p/' in link.get_attribute('href')]
                            posts = []
                            for shortcode in cache[pinned_post_index:]:
                                if shortcode in caught_posts:
                                    pass
                                elif len(caught_posts) == limit:
                                    break
                                else:
                                    posts.append(shortcode)
                                    caught_posts.append(shortcode)
                            if len(posts) == 0:
                                page_load_attempt += 1
                                time.sleep(10)
                            else:
                                browser.save_screenshot(screenshot)
                                log.info(f'Додаю +{len(posts)} скачаних постів з {executor.username}')
                                scheduler.add_job(add_posts, **date(), kwargs=dict(work=work, shortcodes=posts))
                                browser.execute_script(self.button.scroll)
                                time.sleep(7)
                                browser.implicitly_wait(30)
                                page_load_attempt = 0
                        except Exception as Error:
                            log.warning(Error)
                            page_load_attempt += 1

                        if page_load_attempt == 5:
                            browser.close()
                            return
                    if os.path.isfile(screenshot):
                        os.remove(screenshot)
                    scheduler.add_job(
                        name=f'Оновлюю роботу для {executor.username}', func=update_work, **date(),
                        kwargs=dict(work=work, params=update_work_kwargs))
                    browser.close()
                    return
                except Exception as Error:
                    error = self.error_to_html(Error)
                    text = (
                        '#ПомилкаРеєстраціїПостів\n\n'
                        f'Не зміг зареєструвати пости на акаунті {executor.username} '
                        f'{executor.user_id=}\n\n<code>{error}</code>'
                    )
                    error_data = dict(
                        name='Помилка реєстрації постів',
                        description=f'Функція get_posts\n\n{error}', executor_id=executor.account_id,
                        technical=technical.account_id, work_id=work.work_id,
                        proxy_id=self.proxy.id, screenshot=screenshot
                    )
                    scheduler.add_job(
                        send_message, **date(), kwargs=dict(user_id=self.config.misc.error_channel_id,
                                                            text=text, screenshot='None')
                    )
                    scheduler.add_job(
                        name='Створення обєкту помилки', func=create_error, **date(7),
                        kwargs=dict(data=error_data)
                    )

    @staticmethod
    def get_caption(soup: BeautifulSoup):
        try:
            login = soup.find('div', class_='xt0psk2').text
            under_post_text = soup.find_all('div', class_='_a9zr')
            caption = ''
            for text in under_post_text:
                owner = text.find('a').text
                if owner == login:
                    caption = text.find(class_='_aacl _aaco _aacu _aacx _aad7 _aade')
                    break
            answer = ''
            for letter in caption:
                if str(letter) in ('<br>', '<br/>'):
                    answer += '\n'
                else:
                    answer += letter if isinstance(letter, NavigableString) else letter.text
            return answer
        except Exception as Error:
            log.warning(f'Помилка при копіюванні caption:\n{Error}\n')
            return False

    @staticmethod
    def close(browser: webdriver.Chrome):
        try:
            browser.close()
        except:
            pass

    @staticmethod
    def get_post_next_media_button(browser: webdriver.Chrome):
        try:
            window = browser.find_element('class name', '_aao_')
            return window.find_element('class name', '_9zm2')
        except NoSuchElementException:
            return False

    def download_post(self, technicals: list[Account], post: Post, scheduler: ContextSchedulerDecorator):
        for technical in technicals:
            screenshot = self.screen_path.format(technical.username, now().strftime(self.format_time))
            browser = self.login(technical, scheduler)
            if browser:
                try:
                    scheduler.add_job(update_post, **date(), kwargs=dict(post=post,
                                                                         params=dict(status=PostStatusEnum.LOADING)))
                    log.info(f'Відкрив бразузер для {technical.username}...')
                    browser.get(self.post_url.format(post.post_id))
                    time.sleep(5)
                    browser.implicitly_wait(5)
                    if self.is_page_not_available(browser):
                        scheduler.add_job(delete_post, **date(), kwargs=dict(post=post))
                        browser.save_screenshot(screenshot)
                        raise ErrorLoginInstagram('Сторінку не було знайдено')
                    pre_media = []
                    next_button = True
                    soup = BeautifulSoup(browser.page_source, 'lxml')
                    is_video_exist = False
                    while next_button:
                        browser.implicitly_wait(3)
                        presentation = soup.find('div', class_='_aap0')
                        if presentation:
                            images = presentation.find_all('div', class_='_aagv')
                        else:
                            images = soup.find_all('div', class_='_aagv')[:1]
                        logging.info(f'Count media: {len(pre_media)}')
                        videos = soup.find_all(**self.button.videos)
                        if len(images) > 0:
                            for image in images:
                                if image not in pre_media:
                                    pre_media.append(image)
                        if len(videos) > 0:
                            for video in videos:
                                if video not in pre_media:
                                    pre_media.append(video)
                        soup = BeautifulSoup(browser.page_source, 'lxml')
                        if self.is_video_exist(soup):
                            is_video_exist = True
                            break
                        next_button = self.get_post_next_media_button(browser)
                        if next_button:
                            browser.execute_script('arguments[0].click();', next_button)
                        time.sleep(3)

                    browser.save_screenshot(screenshot)
                    caption = self.get_caption(soup)
                    media = []
                    count = 1

                    if is_video_exist:
                        params = {
                            'query_hash': self.button.query_hash,
                            'variables': json.dumps({'shortcode': post.post_id})
                        }
                        response = dict(requests.get(self.graphql_url, params=params,
                                                     proxies=self.proxy.to_dict()).json())
                        if response['status'] == 'fail':
                            pass
                        else:
                            # if not caption:
                            #   caption = response['data']['shortcode_media']['edge_media_to_caption']['edges']
                            #   caption = caption[0]['node']['text'] if caption else ''
                            #   pass
                            if is_video_exist:
                                response = response['data']['shortcode_media']
                                if 'edge_sidecar_to_children' not in list(response.keys()):
                                    video_url = response['video_url']
                                    preview = response['display_url']
                                    media.append(dict(content_type='photo', url=preview, count=count))
                                    media.append(dict(content_type='video', url=video_url, count=count + 1))
                                else:
                                    for edge in response['edge_sidecar_to_children']['edges']:
                                        node = edge['node']
                                        if node['is_video']:
                                            media.append(dict(content_type='video', url=node['video_url'], count=count))
                                        else:
                                            media.append(
                                                dict(content_type='photo', url=node['display_resources'][-1]['src'],
                                                     count=count))
                                        count += 1
                    else:
                        for content in pre_media:
                            content = content.find_all('img')[0].get('src')
                            media.append(dict(content_type='photo', url=content, count=count))
                            count += 1
                    if os.path.isfile(screenshot):
                        os.remove(screenshot)
                    self.close(browser)
                    self.download_media_list(media, caption, post, scheduler)
                    return
                except Exception as Error:
                    self.close(browser)
                    error = self.error_to_html(Error)
                    error_data = dict(
                        name='Помилка скачуванні поста',
                        description=f'Функція download_post\n\n{error}',
                        technical=technical.account_id, post=post.post_id,
                        proxy_id=self.proxy.id, screenshot=screenshot
                    )
                    scheduler.add_job(
                        update_post, **date(), kwargs=dict(post=post, params=dict(status=PostStatusEnum.ACTIVE))
                    )
                    scheduler.add_job(
                        name='Створення обєкту помилки', func=create_error, **date(7),
                        kwargs=dict(data=error_data)
                    )
                    text = (
                        f'#ПомилкаСкачуванняПоста\n\n'
                        f'Не зміг скачати пост #{post.post_id} (account: {post.customer_id}, work: {post.work_id})\n\n'
                        f'<code>{error}</code>'
                    )
                    log.warning(text)
                    scheduler.add_job(
                        func=send_message, **date(), kwargs=dict(user_id=self.config.misc.error_channel_id,
                                                                 text=text, screenshot=screenshot)
                    )
        scheduler.add_job(
            update_post, **date(), kwargs=dict(post=post, params=dict(status=PostStatusEnum.ACTIVE))
        )

    def download_media_list(self, media: list[dict], caption: str, post: Post, scheduler: ContextSchedulerDecorator):
        download_path = self.config.misc.download_path
        size = len(media)
        path = Path(download_path, post.post_id)
        if post.post_id not in os.listdir(download_path):
            os.mkdir(path)
        for content in media:
            content_type = 'jpg' if content['content_type'] == 'photo' else 'mp4'
            filename = path.joinpath(f"file_{content['count']}.{content_type}")
            with open(filename, mode='wb') as file:
                file.write(requests.get(content['url'], proxies=self.proxy.to_dict()).content)
            log.info(f"Post {post.post_id}: {content['count']}/{size}")
        time.sleep(10)
        status = PostStatusEnum.PLAN_PUBLIC if post.is_am_downloaded(self.config) else PostStatusEnum.ACTIVE
        scheduler.add_job(
            update_post, **date(),
            kwargs=dict(post=post, params=dict(caption=caption, mediacount=size, status=status)))

    @staticmethod
    def get_button_coordinates(browser: webdriver.Chrome, name: str):
        buttons = browser.find_elements('tag name', 'button')
        for b in buttons:
            try:
                if b.accessible_name == name:
                    return b.location
            except WebDriverException:
                pass

    @staticmethod
    def click_by_coordinates(browser: webdriver.Chrome, x: float, y: float):
        action = ActionChains(browser)
        action.move_by_offset(x, y)
        action.click()
        action.perform()
        time.sleep(2)

    def check_post_shared_as_reels(self, browser: webdriver.Chrome):
        info = self.get_element_by_name(browser, 'OK', 'button')
        time.sleep(5)
        if info:
            log.info(str(info))
            action = ActionChains(browser)
            action.move_to_element(info)
            action.click()
            action.perform()
            time.sleep(2)
            browser.implicitly_wait(10)

    def upload(self, customer: Account, post: Post, scheduler: ContextSchedulerDecorator):
        screenshot = self.screen_path.format(customer.username, now().strftime(self.format_time))
        button_name = 'default'
        browser = self.login(customer, scheduler)
        try:
            if not browser:
                raise ErrorLoginInstagram(f'Не зміг увійти в акаунт {customer.username}')
            media_group = post.get_post_files(self.config)
            if self.is_exist(*self.button.create):
                self.click(*self.button.create, browser=browser)
            else:
                cord = self.get_button_coordinates(browser, 'New post')
                self.click_by_coordinates(browser, **cord)
            time.sleep(2)
            browser.implicitly_wait(10)
            self.click(*self.button.select_file, browser=browser)
            browser.save_screenshot(screenshot)
            upload = browser.find_elements(*self.button.input)[-1]
            upload.send_keys(media_group[0])
            time.sleep(3)
            self.check_post_shared_as_reels(browser)
            browser.implicitly_wait(10)
            crop = self.get_element_by_name(browser, 'Select crop', tag='button')
            button_name = 'crop'
            browser.execute_script('arguments[0].click();', crop)
            time.sleep(2)
            browser.implicitly_wait(10)
            original = self.get_element_by_name(browser, 'Original', tag='button')
            button_name = 'original'
            browser.execute_script('arguments[0].click();', original)
            time.sleep(2)
            browser.execute_script('arguments[0].click();', crop)
            time.sleep(2)
            browser.save_screenshot(screenshot)
            self.check_post_shared_as_reels(browser)
            if len(media_group) > 1:
                for media in media_group[1:]:
                    b = self.get_element_by_name(browser, 'Open media gallery', tag='button')
                    button_name = 'open media gallery'
                    browser.execute_script('arguments[0].click();', b)
                    time.sleep(2)
                    browser.find_element(
                        'css selector',
                        '[accept="image/jpeg,image/png,image/heic,image/heif,video/mp4,video/quicktime"]'
                    ).send_keys(media)
                    browser.save_screenshot(screenshot)
                    time.sleep(5)
                    self.check_post_shared_as_reels(browser)
                    right = self.get_element_by_name(browser, 'Right chevron', tag='button')
                    button_name = 'right chevron'
                    browser.execute_script('arguments[0].click();', right)
                    time.sleep(2)
                    button_name = 'Open media gallery NEXT'
                    browser.execute_script('arguments[0].click();', b)
                    time.sleep(2)
                    browser.implicitly_wait(10)
                    self.check_post_shared_as_reels(browser)
            browser.save_screenshot(screenshot)
            self.check_post_shared_as_reels(browser)
            if len(browser.window_handles) > 1:
                time.sleep(2)
                browser.switch_to.window(browser.window_handles[-1])
                browser.close()
                browser.switch_to.window(browser.window_handles[0])
                time.sleep(2)
            browser.save_screenshot(screenshot)
            for i in range(2):
                next_button = self.get_element_by_name(browser, 'Next', tag='div', reverse=True)
                browser.execute_script('arguments[0].click();', next_button)
                button_name = 'next'
                time.sleep(5)
                browser.implicitly_wait(10)
                browser.save_screenshot(screenshot)
            if post.caption is not None:
                caption_textarea = self.get_element_by_name(browser, 'Write a caption...', tag='textarea')
                caption_div = self.get_element_by_name(browser, 'Write a caption...', tag='div')
                caption_area = caption_textarea if caption_textarea else caption_div
                for letter in post.caption:
                    letter = str(letter)
                    try:
                        caption_area.send_keys(letter)
                    except:
                        pass
            time.sleep(1)
            click_area_post = self.get_element_by_name(browser, 'Create new post', tag='div', text=True, reverse=True)
            click_area_reel = self.get_element_by_name(browser, 'New reel', tag='div', text=True, reverse=True)
            click_area = click_area_post if click_area_post else click_area_reel
            action = ActionChains(browser)
            action.move_to_element(click_area)
            action.click(on_element=click_area)
            action.perform()
            time.sleep(2)
            share_button = self.get_element_by_name(browser, 'Share', tag='div', reverse=True)
            button_name = 'share button'
            browser.execute_script('arguments[0].click();', share_button)
            time.sleep(2)
            self.close(browser)
            if os.path.isfile(screenshot):
                os.remove(screenshot)
            scheduler.add_job(update_post, **date(), kwargs=dict(
                post=post, params=dict(status=PostStatusEnum.DONE)
            ))
            post.delete_me(self.config)
        except Exception as Error:
            self.close(browser)
            error = self.error_to_html(Error)
            scheduler.add_job(update_post, **date(), kwargs=dict(
                post=post, params=dict(status=PostStatusEnum.PLAN_PUBLIC)
            ))
            text = (
                f'#ПомилкаПублікуванняПоста\n\n'
                f'Не зміг опубілкувати пост #{post.post_id} для {customer.username}\n\n'
                f'<code>{error}; {button_name=}</code>'
            )
            error_data = dict(
                name='Помилка публікуванні поста',
                description=f'Функція upload ({button_name=})\n\n{error}',
                customer_id=customer.account_id, post=post.post_id,
                proxy_id=self.proxy.id, screenshot=screenshot
            )
            scheduler.add_job(
                name='Створення обєкту помилки', func=create_error, **date(7),
                kwargs=dict(data=error_data)
            )
            scheduler.add_job(
                func=send_message, **date(), kwargs=dict(user_id=self.config.misc.error_channel_id,
                                                         text=text, screenshot=screenshot)
            )


async def test(scheduler: ContextSchedulerDecorator, session: sessionmaker, controller: ProxyController):
    from app.instagram.misc import database
    db = database(session)
    i = InstagramController(await db.proxy_db.get_proxy(2))
    log.info('Відкриваю перший')
    i.set_browser()
    time.sleep(1)
    i.close(i.browser)
    time.sleep(1)
    i = InstagramController(await db.proxy_db.get_proxy(2))
    log.info('Відкриваю другий')
    i.set_browser()
    time.sleep(1)
    i.close(i.browser)