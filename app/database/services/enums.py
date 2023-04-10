from enum import Enum


class AccountStatusEnum(Enum):
    ACTIVE = 'ACTIVE'
    BANNED = 'BANNED'
    PAUSE = 'PAUSE'
    UNPAID = 'UNPAID'


class AccountTypeEnum(Enum):
    TECHNICAL = 'TECHNICAL'
    PARSING = 'PARSING'
    POSTING = 'POSTING'


class WorkModeEnum(Enum):
    ALL = 'ALL'
    ONLY_NEW = 'ONLY_NEW'
    ALL_AND_NEW = 'ALL_AND_NEW'
    LAST_N = 'LAST_N'


class PostStatusEnum(Enum):
    ACTIVE = 'ACTIVE'
    PLAN_DOWNLOAD = 'PLAN_DOWNLOAD'
    LOADING = 'LOADING'
    PLAN_PUBLIC = 'PLAN_PUBLIC'
    WAIT_PUBLIC = 'WAIT_PUBLIC'
    DONE = 'DONE'
    PAUSE = 'PAUSE'


class WorkStatusEnum(Enum):
    ACTIVE = 'ACTIVE'
    DONE = 'DONE'


class UserStatusEnum(Enum):
    ACTIVE = 'ACTIVE'
    TRIAL = 'TRIAL'
