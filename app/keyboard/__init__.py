from dataclasses import dataclass


@dataclass
class Work:
    all: str = 'Всі пости'
    all_and_new: str = 'Всі та нові'
    only_new: str = 'Тільки нові'
    last_n: str = 'Останні X постів'


@dataclass
class Accounts:
    work = Work()
    pay: str = '💳 Купити підписку'
    statistic: str = '📊 Статистика'
    detail_statistic = 'Детальніше про пости...'
    limit: str = '🕑 Ліміт публікацій'
    refresh_status: str = 'Відновити публікації ✅'
    login_data: str = '📲 Дані для Інстаграм'
    delete: str = '🗑 Видалити'
    add_work: str = '➕ Додати завдання'
    del_work: str = '➖ Видалити завдання'
    pause: str = '⏸ Зупинити'
    resume: str = '▶ Запустити'
    settings: str = '⚙ Налаштування'
    auth_help: str = '💭 Інструкція'
    update: str = '🔄 Оновити'
    confirm: str = 'Підтверджую ✔'
    developer: str = '🔧 Для розробника'
    edit_username: str = 'Юзернейм'
    edit_password: str = 'Пароль'
    edit_auth_key: str = 'Ключ двоетапної перевірки'
    back: str = 'Назад'
    skip: str = 'Пропустити ▶'


@dataclass
class Admin:
    technicals: str = '🤖 Технічні акаунти'
    download: str = '🗂 Скачати Excel'
    subscribe: str = '💳 Підписка'
    update: str = 'Оновити'
    root: str = '💎 root'
    proxy: str = '🌍 Проксі'
    back: str = 'Назад'


@dataclass
class Menu:
    admin: str = '💻 Панель адміністратора'
    add_account: str = '➕ Додати акаунт'
    my_accounts: str = '📱 Мої акаунти'
    to_posting: str = '📤 Публікація'
    to_parsing: str = '📂 Копіювання'
    subscription: str = '💳 Підписка'
    help: str = '💬 Підтримка'
    FAQ: str = 'ЧаПи'
    back: str = '◀ Назад'


@dataclass
class Buttons:
    menu = Menu()
    admin = Admin()
    accounts = Accounts()