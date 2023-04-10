from app.database.models import Work, Account
from app.database.services.enums import WorkStatusEnum, WorkModeEnum, AccountStatusEnum


def construct_accounts_list(accounts: list[Account], current_account: Account):
    text = ''
    for account, num in zip(accounts, range(1, len(accounts) + 1)):
        marker = '*' if account.status == AccountStatusEnum.BANNED else ''
        brackets = ('<b>[', ']</b>') if account.username == current_account.username else ('', '')
        text += f'{num}. {brackets[0]}{account.username}{marker}{brackets[-1]}\n'
    return text


def construct_work_status(work: Work):
    if work.status == WorkStatusEnum.ACTIVE:
        return '🆕'
    else:
        return '✔'


def construct_work_mode(work: Work):
    if work.mode == WorkModeEnum.ALL:
        return 'Всі пости'
    elif work.mode == WorkModeEnum.ONLY_NEW:
        return 'Тільки нові пости'
    elif work.mode == WorkModeEnum.ALL_AND_NEW:
        return 'Усі та нові пости'
    elif work.mode == WorkModeEnum.LAST_N:
        return f'Останні {work.limit} постів'
