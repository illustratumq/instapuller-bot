import logging
import random
import shutil
from dataclasses import dataclass

import pyotp
import time
from pathlib import Path
import requests
import platform
import json

from apscheduler_di import ContextSchedulerDecorator
from bs4 import BeautifulSoup, NavigableString
from selenium import webdriver
from selenium.common import NoSuchElementException, WebDriverException
from selenium.webdriver import Keys, ActionChains
import pickle

from app.config import Config
from app.instagram.methods.methods import *
from app.instagram.proxy.proxy import ProxyComposter
from app.misc.enums import PostStatusEnum, WorkModeEnum, WorkStatusEnum, AccountStatusEnum
from app.misc.utils import now
from app.models.account import Account
from app.models.post import Post
from app.models.work import Work


DEVICE = Device.WINDOWS if platform.system().lower() == 'windows' else Device.SERVER

config = Config.from_env()

log = logging.getLogger(__name__)
format_time = '%d_%m_%Y_%H_%M_%S'


def only_bmp_char(string: str):
    _str = ''
    for i in string:
        if len(i.encode()) < 3:
            _str += i
    return _str


@dataclass
class Button:
    login: tuple = 'xpath', '//*[@id="loginForm"]/div/div[1]/div/label/input'
    password: tuple = 'xpath', '//*[@id="loginForm"]/div/div[2]/div/label/input'
    entry: tuple = 'xpath', '//*[@id="loginForm"]/div/div[3]/button'
    accept_cookies: tuple = 'xpath', '//button[contains(text(), "Not Now")]'
    save_session: tuple = 'xpath', '//*[@id="react-root"]/section/main/div/div/div/div/button'
    new_media: str = 'xpath', '//button[contains(text(), "New post")]'
    select_file: tuple = 'xpath', "//*[contains(text(), 'Select from computer')]"
    input: tuple = 'tag name', 'input'
    next: tuple = 'xpath', '//button[contains(text(), "Next")]'
    caption: tuple = 'tag name', 'textarea'
    share: tuple = 'xpath', '//button[contains(text(), "Share")]'
    security: tuple = 'css selector', "[aria-label='Security Code']"
    confirm: tuple = 'xpath', "//*[contains(text(), 'Confirm')]"
    media_count: tuple = 'xpath', '/html/body/div[1]/div/div/div/div[1]/div/div/div/div[1]/section' \
                                  '/main/div/header/section/ul/li[1]/div/span'
    post_count: tuple = 'class name', '_ac2a'
    create = 'xpath', "//*[contains(text(), 'Create')]"
    new_post = 'xpath', "//*[contains(text(), 'New post')]"
    error: tuple = 'xpath', '//*[@id="slfErrorAlert"]'
    not_profile: tuple = 'xpath', '/html/body/div[2]/div/div/div/div[1]/div/div/div/div[1]/div[1]/div[2]/section/main/div/div/div/h2'

    #  LOADING

    scroll: str = 'window.scrollTo(0, document.body.scrollHeight);'
    query_hash: str = '2b0673e0dc4580674a88d426fe00ea90'
    images = {'name': 'div', 'class_': '_aagu _aato'}
    images_closed = {'name': 'div', 'class_': '_aagu _aa20 _aato'}
    image = {'name': 'div', 'class_': '_aagv'}
    videos = {'name': 'div', 'class_': '_ab1c'}


class ErrorLoginInstagram(Exception):
    pass


class instagram_controller:

    login_url = 'https://www.instagram.com'
    post_url = 'https://www.instagram.com/p/{}'
    profile_url = 'https://www.instagram.com/{}'
    graphql_url = 'https://www.instagram.com/graphql/query'

    screen_path = 'app/instagram/screenshots/{}_{}.png'
    cookies_form = '{}_cookies.pkl'

    def __init__(
            self,
            proxy: str = None,
            sleep: tuple = (5, 10),
            cookies_path: str = 'app/instagram/cookies'
    ):
        self.config = Config.from_env()
        self.proxy = proxy
        self.sleep = sleep
        self.cookies_path = cookies_path
        self.browser = None
        self.button = Button()
        self.proxy_composter = ProxyComposter('app/instagram/proxy/proxy.json')

    def set_browser(self):
        if DEVICE == Device.WINDOWS:
            self.set_browser_windows()
            return
        for i in [4, 5, 6, 7, 8]:
            try:
                log.warning(f'Спроба підключитись на порт 444{i}')
                self.browser = webdriver.Remote(command_executor=f'http://selenoid:444{i}/wd/hub', **self.options())
                break
            except:
                log.warning(f'Не зміг підключитись до хрому з 444{i}')
                continue

    #  WINDOWS MODE
    def set_browser_windows(self):
        self.browser = webdriver.Chrome(**self.windows_options())
        self.browser.get('https://ipinfo.io/json')
        time.sleep(1)


    def windows_options(self) -> dict:
        options = webdriver.ChromeOptions()
        options.add_argument("--lang=eng")
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--ignore-ssl-errors=yes')
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        result = dict(options=options)
        desired_capabilities = {
            'browserName': 'chrome',
            'version': 'latest',
            'platform': 'WINDOWS',
        }

        if isinstance(self.proxy, str):
            self.proxy_composter.use_proxy(self.proxy)
            host, port, proxy_type, url = self.proxy.split(';')
            proxy_config = dict(proxyType='MANUAL')
            proxy_string = f'{host}:{port}'
            if 'socks' in proxy_type:
                proxy_config.update(socksVersion=5, socksProxy=proxy_string)
            else:
                proxy_config.update(httpProxy=proxy_string, frpProxy=proxy_string, sslProxy=proxy_string)
            desired_capabilities.update(proxy=proxy_config)
            result.update(desired_capabilities=desired_capabilities)

        return result

    def options(self) -> dict:
        options = webdriver.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument("--lang=eng")
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--ignore-ssl-errors=yes')
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option("detach", True)
        desired_capabilities = {
            'browserName': 'chrome',
            'version': 'latest',
            'platform': 'LINUX',
        }

        result = dict(options=options, desired_capabilities=desired_capabilities)

        if isinstance(self.proxy, str):
            self.proxy_composter.use_proxy(self.proxy)
            host, port, proxy_type, url = self.proxy.split(';')
            proxy_config = dict(proxyType='MANUAL')
            proxy_string = f'{host}:{port}'
            if 'socks' in proxy_type:
                proxy_config.update(socksVersion=5, socksProxy=proxy_string)
            else:
                proxy_config.update(httpProxy=proxy_string, frpProxy=proxy_string, sslProxy=proxy_string)
            desired_capabilities.update(proxy=proxy_config)
            result.update(desired_capabilities=desired_capabilities)

        return result

    def random_sleep(self, custom_seconds: tuple = None):
        seconds = self.sleep if custom_seconds is None else custom_seconds
        k = 1.5 if isinstance(self.proxy, str) else 1
        time.sleep(random.randint(int(seconds[0]*k), int(seconds[-1]*k)))

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
        time.sleep(3)

    def confirmations(self, browser: webdriver.Chrome):
        self.click(*self.button.accept_cookies, browser=browser, check_exist=True)

    def save_cookies(self, browser: webdriver.Chrome, login: str):
        log.info(f'Save cookies for {login}')
        with open(Path(self.cookies_path, self.cookies_form.format(login)), mode='wb') as file:
            pickle.dump(browser.get_cookies(), file)
        self.random_sleep()

    def get_cookies(self, browser: webdriver.Chrome, login: str) -> webdriver.Chrome:
        log.info(f'Load cookies for {login}')
        with open(Path(self.cookies_path, self.cookies_form.format(login)), 'rb') as file:
            cookies = pickle.load(file)
            browser.delete_all_cookies()
            for cookie in cookies:
                browser.add_cookie(cookie)
            browser.refresh()
        self.random_sleep()
        self.confirmations(browser)
        return browser

    def is_cookies_exist(self, login: str):
        return self.cookies_form.format(login) in os.listdir(self.cookies_path)

    @staticmethod
    def close(browser: webdriver.Chrome):
        browser.close()
        browser.quit()

    def click_by_coordinates(self, browser: webdriver.Chrome, x: float, y: float):
        action = ActionChains(browser)
        action.move_by_offset(x, y)
        action.click()
        action.perform()
        self.random_sleep()

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
    def is_page_available(browser: webdriver.Chrome):
        return 'Sorry, this page isn\'t available.' in browser.page_source

    @staticmethod
    def get_button(browser: webdriver.Chrome, name: str):
        buttons = browser.find_elements('tag name', 'button')
        for b in buttons:
            try:
                if b.accessible_name == name:
                    return b
            except WebDriverException:
                pass

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
            log.warning(f'Failed to get caption:\n{Error}\n')
            return False

    @staticmethod
    def get_auth_keycode(key: str):
        for i in range(2):
            code = pyotp.TOTP(key.replace(' ', ''))
            time_remaining = int(code.interval - datetime.now().timestamp() % code.interval)
            if time_remaining >= 5:
                return code.now()
            else:
                time.sleep(6)

    def login(self, login: str, password: str, user_id: int,
              scheduler: ContextSchedulerDecorator, key: str = None) -> webdriver.Chrome | Exception:
        screenshot = self.screen_path.format(login, now().strftime(format_time))
        cookies = self.is_cookies_exist(login)
        try:
            for step in [1, 2]:
                run = True
                log.info(f'Login in {login}. Attempt {step}/2')
                self.set_browser()
                browser = self.browser
                browser.get(self.login_url)
                self.random_sleep((5, 6))
                browser.save_screenshot(screenshot)
                allow_cookies = self.get_button(browser, 'Allow essential and optional cookies')
                if allow_cookies:
                    allow_cookies.click()
                    self.random_sleep(custom_seconds=(5, 7))
                if cookies:
                    file_empty = False
                    try:
                        browser = self.get_cookies(browser, login)
                    except:
                        os.remove(f'{self.cookies_path}/{self.cookies_form.format(login)}')
                        file_empty = True
                    if not file_empty:
                        time.sleep(2)
                        if self.get_element_by_name(browser, 'Send confirmation code', tag='button'):
                            raise ErrorLoginInstagram('Бот не зміг увійти в ваш акаунт, схоже вам треба підтвердити '
                                                      'вхід в акаунт вручну.')
                        if self.get_element_by_name(browser, 'Phone number, username, or email', tag='input'):
                            browser.get_screenshot_as_file(screenshot)
                            # os.remove(f'{self.cookies_path}/{self.cookies_form.format(login)}')
                            # log.info(f'Removing cookies for {login}')
                            cookies = False
                            run = False
                        else:
                            return browser
                if run:
                    self.get_element_by_name(browser, 'Phone number, username, or email', tag='input').send_keys(login)
                    self.random_sleep((3, 4))
                    self.get_element_by_name(browser, 'Password', tag='input').send_keys(password)
                    self.random_sleep(custom_seconds=(2, 4))
                    browser.find_element(*self.button.entry).send_keys(Keys.ENTER)
                    self.random_sleep(custom_seconds=(7, 10))
                    browser.get_screenshot_as_file(screenshot)
                    if self.is_exist(*self.button.error):
                        error = browser.find_element(*self.button.error).text
                        raise ErrorLoginInstagram(error)
                    if key:
                        button = browser.find_element(*self.button.security)
                        if button is not None:
                            button.send_keys(self.get_auth_keycode(key))
                            self.click(*self.button.confirm, browser=browser)
                            self.random_sleep()
                            self.save_cookies(browser, login)
                            browser.get_screenshot_as_file(screenshot)
                            if not self.is_exist(*self.button.create) and self.get_button(browser, 'New post') is None:
                                raise ErrorLoginInstagram('Бот не зміг увійти в ваш акаунт. Схоже ваш код двоетапної '
                                                          'перевірки не правильний. Зверніться в підтримку щоб '
                                                          'редагувати його.')
                    browser.save_screenshot(screenshot)
                    post_blocked = self.get_button(browser, 'OK')
                    if post_blocked:
                        post_blocked.send_keys(Keys.ENTER)
                        self.random_sleep()
                    self.confirmations(browser)
                    self.random_sleep((10, 10))
                    if not self.is_exist(*self.button.create) and self.get_button(browser, 'New post') is None:
                        raise ErrorLoginInstagram('Бот не зміг увійти в ваш акаунт.')
                    if not cookies:
                        self.save_cookies(browser, login)
                    log.info(f'Successfully login for {login}')
                    os.remove(screenshot)
                    return browser
        except Exception as Error:
            error = str(Error).replace('<', '').replace('>', '')
            scheduler.add_job(send_screenshot, **run_func(), kwargs=dict(
                screenshot=screenshot, caption=f'<b>Помилка при вході в акаунт {login}\n\n{error}</b>', user_id=user_id
            ))
            self.browser.close()
            return Error

    def get_posts(self, technical: Account, executor: Account, customer: Account,
                  work: Work, scheduler: ContextSchedulerDecorator):
        screenshot = self.screen_path.format(executor.username, now().strftime(format_time))
        posts = []
        try:
            browser = self.login(technical.username, technical.password, executor.user_id, scheduler,
                                 technical.authentication_key)
            if isinstance(browser, Exception):
                scheduler.add_job(update_account, **run_func(),
                                  kwargs=dict(account=technical, kwargs=dict(status=AccountStatusEnum.BANNED)))
                raise ErrorLoginInstagram(browser)
            browser.save_screenshot(screenshot)
            browser.get(self.profile_url.format(executor.username))
            self.random_sleep((5, 6))

            browser.save_screenshot(screenshot)
            if len(browser.find_elements(*self.button.post_count)) == 0:
                raise ErrorLoginInstagram(f'Cannot open {executor.username} profile by {technical.username}')
            current_media_count = int(browser.find_elements(*self.button.post_count)[0].text.replace(',', ''))
            logging.info(f'Open {executor.username} account with {current_media_count} posts')
            base_kwargs = dict(mediacount=current_media_count)
            if work.mode == WorkModeEnum.ONLY_NEW:
                if work.mediacount == 0:
                    scheduler.add_job(update_work, **run_func(), kwargs=dict(kwargs=base_kwargs, work=work))
                    os.remove(screenshot)
                    return
                if current_media_count == work.mediacount:
                    os.remove(screenshot)
                    return
                limit = current_media_count - work.mediacount + 3
            elif work.mode == WorkModeEnum.ALL_AND_NEW:
                limit = current_media_count
                base_kwargs.update(mode=WorkModeEnum.ONLY_NEW)
            elif work.mode == WorkModeEnum.ALL:
                limit = current_media_count
                base_kwargs.update(status=WorkStatusEnum.DONE)
            else:
                limit = executor.limit
                base_kwargs.update(status=WorkStatusEnum.DONE)

            scheduler.add_job(update_work, **run_func(), kwargs=dict(kwargs=base_kwargs, work=work))

            control_while = 0
            list_counter = 0
            logging.info(f'Start catching posts in limit: {limit}')

            while len(posts) < limit:
                self.random_sleep((5, 6))
                if control_while == 5:
                    break
                now_in_lst = 0
                hrefs = browser.find_elements('tag name', 'a')
                cache = [href.get_attribute('href') for href in hrefs if '/p/' in href.get_attribute('href')]
                for post in cache:
                    if post not in posts:
                        if len(posts) == limit:
                            break
                        else:
                            posts.append(post)
                            now_in_lst += 1
                browser.save_screenshot(screenshot)
                if list_counter == len(posts):
                    control_while += 1
                else:
                    control_while = 0
                browser.execute_script(self.button.scroll)
                self.random_sleep((5, 6))
                list_counter = len(posts)
            self.close(browser)
            logging.info(f'Catch posts in size: {len(posts)}')
            os.remove(screenshot)
            scheduler.add_job(add_posts_to_db, **run_func(), kwargs=dict(
                posts=posts, work=work, customer=customer, executor=executor
            ))
        except Exception as Error:
            error = str(Error).replace('<', '').replace('>', '')
            scheduler.add_job(send_screenshot, **run_func(5), kwargs=dict(
                screenshot=screenshot, caption=f'Помилка при реєстрації постів {executor.username}\n\n{error}',
                user_id=config.bot.admin_ids
            ))
            log.error(f'Помилка при реєстрації постів {technical.username=}, {executor.username=}')
            scheduler.add_job(update_work, **run_func(10),
                              kwargs=dict(kwargs=dict(status=WorkStatusEnum.ACTIVE), work=work))

    def download_post(self, technical: Account, shortcode: str, user_id, scheduler: ContextSchedulerDecorator,
                      key: str = None):
        screenshot = self.screen_path.format(technical.username, now().strftime(format_time))
        try:
            browser = self.login(technical.username, technical.password, user_id, scheduler, key)
            if isinstance(browser, Exception):
                scheduler.add_job(update_account, **run_func(),
                                  kwargs=dict(account=technical, kwargs=dict(status=AccountStatusEnum.BANNED)))
                raise ErrorLoginInstagram(browser)
            browser.get(self.post_url.format(shortcode))
            self.random_sleep((5, 6))
            browser.save_screenshot(screenshot)
            if self.is_page_available(browser):
                scheduler.add_job(delete_post, **run_func(10), kwargs=dict(post_id=shortcode))
                scheduler.add_job(account_increment, **run_func(15), kwargs=dict(post_id=shortcode))
            pre_media = []
            next_button = True
            soup = BeautifulSoup(browser.page_source, 'lxml')
            is_video_exist = False
            while next_button is not None:
                next_button = self.get_button(browser, 'Next')
                if next_button:
                    browser.execute_script('arguments[0].click();', next_button)
                self.random_sleep((2, 3))
                images = soup.find_all(**self.button.images_closed)
                images += soup.find_all(**self.button.images)
                logging.info(f'Count images: {len(images)}')
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
            browser.save_screenshot(screenshot)
            self.close(browser)

            caption = self.get_caption(soup)
            media = []
            count = 1

            if is_video_exist:
                proxies = self.get_proxies
                params = {
                    'query_hash': self.button.query_hash,
                    'variables': json.dumps({'shortcode': shortcode})
                }
                response = dict(requests.get(self.graphql_url, params=params, proxies=proxies).json())
                if response['status'] == 'fail':
                    pass
                else:
                    if not caption:
                        # caption = response['data']['shortcode_media']['edge_media_to_caption']['edges']
                        # caption = caption[0]['node']['text'] if caption else ''
                        pass
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
                                        dict(content_type='photo', url=node['display_resources'][-1]['src'], count=count))
                                count += 1
            else:
                for content in pre_media:
                    content = content.find_all(**self.button.image)[0].find_all('img')[0].get('src')
                    media.append(dict(content_type='photo', url=content, count=count))
                    count += 1
            self.download_media_list(media, caption, shortcode, scheduler)
        except Exception as Error:
            error = str(Error).replace('<', '').replace('>', '')
            scheduler.add_job(update_post, **run_func(), kwargs=dict(
                post_id=shortcode, kwargs=dict(status=PostStatusEnum.ACTIVE)
            ))
            scheduler.add_job(send_screenshot, **run_func(), kwargs=dict(
                screenshot=screenshot, caption=f'Помилка при скачування поста {shortcode} by'
                                               f' {technical.username}\n\n{error}',
                user_id=config.bot.admin_ids
            ))

    @staticmethod
    def is_video_exist(soup: BeautifulSoup) -> bool:
        return len(soup.find_all('div', class_='_ab1c')) + len(soup.find_all('video')) > 0

    def download_media_list(self, media: list[dict], caption: str, shortcode: str, scheduler: ContextSchedulerDecorator):
        download_path = Config.from_env().misc.download_path
        size = len(media)
        path = Path(download_path, shortcode)
        if shortcode not in os.listdir(download_path):
            os.mkdir(path)
        for content in media:
            content_type = 'jpg' if content['content_type'] == 'photo' else 'mp4'
            filename = path.joinpath(f"file_{content['count']}.{content_type}")
            with open(filename, mode='wb') as file:
                file.write(requests.get(content['url'], proxies=self.get_proxies).content)
            log.info(f"Post {shortcode}: {content['count']}/{size}")
        scheduler.add_job(update_post, **run_func(), kwargs=dict(
            post_id=shortcode, kwargs=dict(caption=caption, status=PostStatusEnum.LOADING)
        ))

    def reboot_proxies(self):
        host, port, proxy_type, url = self.proxy.split(';')
        try:
            answer = requests.get(url).json()
            time.sleep(10)
            log.warning(f'Reboot proxy {host}:{port}! Status: {answer["status"]}')
        except:
            log.error(f'Incorrect url or connection error with proxy: {host}:{port}:{url}')

    @property
    def get_proxies(self):
        host, port, proxy_type, reboot_url = self.proxy.split(';')
        proxies = {
            'http': f'{proxy_type}://{host}:{port}',
            'https': f'{proxy_type}://{host}:{port}'
        }
        return proxies

    def upload(self, media_group: list[str], customer: Account, post: Post, scheduler: ContextSchedulerDecorator):
        key = None if customer.authentication_key == '' else customer.authentication_key
        screenshot = self.screen_path.format(customer.username, now().strftime(format_time))
        try:
            browser = self.login(customer.username, customer.password, customer.user_id, scheduler, key)
            if isinstance(browser, Exception):
                text = (
                    f'Виникла помилка, під час входу в акаунт {customer.username}. Я перевожу акаунт в статус '
                    f'"заблоковано", всі дії тимчасово призупинені. Для відновлення роботи напишіть у підтримку.'
                )
                scheduler.add_job(update_account, **run_func(),
                                  kwargs=dict(account=customer, kwargs=dict(status=AccountStatusEnum.BANNED)))
                scheduler.add_job(send_message, **run_func(),
                                  kwargs=dict(bot=Bot, user_id=customer.user_id, text=text))
                raise ErrorLoginInstagram(browser)
            button = self.button
            self.confirmations(browser)
            browser.save_screenshot(screenshot)
            if self.is_exist(*self.button.create):
                self.click(*self.button.create, browser=browser)
            else:
                cord = self.get_button_coordinates(browser, 'New post')
                self.click_by_coordinates(browser, **cord)
            self.click(*button.select_file, browser=browser)
            upload = browser.find_elements(*button.input)[-1]
            upload.send_keys(media_group[0])
            self.random_sleep((3, 4))
            crop = self.get_element_by_name(browser, 'Select crop', tag='button')
            browser.execute_script('arguments[0].click();', crop)
            self.random_sleep((1, 2))
            original = self.get_element_by_name(browser, 'Original', tag='button')
            browser.execute_script('arguments[0].click();', original)
            self.random_sleep((1, 2))
            browser.execute_script('arguments[0].click();', crop)
            self.random_sleep((1, 2))
            browser.save_screenshot(screenshot)
            if len(media_group) > 1:
                for media in media_group[1:]:
                    b = self.get_element_by_name(browser, 'Open media gallery', tag='button')
                    browser.execute_script('arguments[0].click();', b)
                    self.random_sleep((1, 2))
                    browser.find_element(
                        'css selector',
                        '[accept="image/jpeg,image/png,image/heic,image/heif,video/mp4,video/quicktime"]'
                    ).send_keys(media)
                    self.random_sleep((2, 3))
                    right = self.get_element_by_name(browser, 'Right chevron', tag='button')
                    browser.execute_script('arguments[0].click();', right)
                    self.random_sleep((4, 5))
                    browser.execute_script('arguments[0].click();', b)
                    self.random_sleep((1, 2))
            browser.save_screenshot(screenshot)
            info = self.get_button(browser, 'OK')
            if info:
                info.send_keys(Keys.ENTER)
                self.random_sleep()
            self.click(*button.next, browser=browser)
            self.random_sleep((1, 2))
            self.click(*button.next, browser=browser)
            self.random_sleep((1, 2))
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
                self.random_sleep((1, 2))
            click_area = self.get_element_by_name(browser, 'Create new post', tag='div', text=True)
            action = ActionChains(browser)
            action.move_to_element(click_area)
            action.click(on_element=click_area)
            action.perform()
            self.random_sleep((1, 2))
            self.click(*button.share, browser=browser)
            self.random_sleep((1, 2))
            browser.save_screenshot(screenshot)
            self.close(browser)
            scheduler.add_job(update_post, **run_func(), kwargs=dict(
                post_id=post.post_id, kwargs=dict(status=PostStatusEnum.DONE)
            ))
            shutil.rmtree(Path(config.misc.download_path, post.post_id))
            os.remove(screenshot)
        except Exception as Error:
            error = str(Error).replace('<', '').replace('>', '')
            scheduler.add_job(update_post, **run_func(), kwargs=dict(
                post_id=post.post_id, kwargs=dict(status=PostStatusEnum.PLAN_PUBLIC)
            ))
            log.warning(f'\nПомилка при публікації поста  ({post.post_id}) для {customer.username}\n\n{Error}')
            scheduler.add_job(send_screenshot, **run_func(), kwargs=dict(
                screenshot=screenshot, caption=f'Помилка публікації поста {post.post_id}\n\n{error}',
                user_id=customer.user_id
            ))

    def check_account_exist(self, technicals: list[Account], username: str, user_id: int, true_func, false_func,
                            scheduler: ContextSchedulerDecorator, kwargs: dict):
        technicals_count = len(technicals)
        c = 1
        for technical in technicals:
            log.error(f'Login {technical.username} [{c}/{technicals_count}]')
            browser = self.login(technical.username, technical.password, self.config.bot.admin_ids[0], scheduler,
                                 technical.authentication_key)
            if isinstance(browser, Exception):
                scheduler.add_job(update_account, **run_func(),
                                  kwargs=dict(account=technical, kwargs=dict(status=AccountStatusEnum.BANNED)))
            else:
                browser.get(self.profile_url.format(username))
                self.random_sleep((5, 6))
                not_found = self.is_exist(*self.button.not_profile)
                if not not_found:
                    scheduler.add_job(true_func, **run_func(), kwargs=kwargs)
                else:
                    scheduler.add_job(false_func, **run_func(), kwargs=kwargs)
                self.close(browser)
                return
            c += 1
        scheduler.add_job(false_func, **run_func(), kwargs=kwargs)

    def check_login(self, login: str, password: str, user_id: int, true_func, false_func,
                    scheduler: ContextSchedulerDecorator, kwargs: dict, key: str = None):
        browser = self.login(login, password, self.config.bot.admin_ids[0], scheduler, key)
        if isinstance(browser, Exception):
            scheduler.add_job(false_func, **run_func(), kwargs=kwargs, name=f'false_func[{login}]')
        else:
            scheduler.add_job(true_func, **run_func(), kwargs=kwargs, name=f'true_func[{login}]')
        self.close(browser)
