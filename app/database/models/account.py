import sqlalchemy as sa
from sqlalchemy import TIMESTAMP
from sqlalchemy.dialects.postgresql import ENUM

from app.database.services.enums import AccountTypeEnum, AccountStatusEnum
from app.database.models.base import TimedBaseModel
from sqlalchemy import func


class Account(TimedBaseModel):
    account_id = sa.Column(sa.BIGINT, primary_key=True, autoincrement=True)
    user_id = sa.Column(sa.BIGINT, sa.ForeignKey('users.user_id', ondelete='SET NULL'), nullable=True)
    username = sa.Column(sa.VARCHAR(255), nullable=False)
    password = sa.Column(sa.VARCHAR(255), nullable=True)
    auth_key = sa.Column(sa.VARCHAR(255), nullable=True)
    limit = sa.Column(sa.INTEGER, nullable=False, default=25)
    free_action = sa.Column(sa.INTEGER, nullable=False, default=25)
    type = sa.Column(ENUM(AccountTypeEnum), nullable=False, default=AccountTypeEnum.TECHNICAL)
    status = sa.Column(ENUM(AccountStatusEnum), nullable=False, default=AccountStatusEnum.ACTIVE)
    subscript_date = sa.Column(TIMESTAMP(timezone=True), nullable=True)
    subscript_days = sa.Column(sa.INTEGER, default=30, nullable=False)

    def get_status_string(self):
        if self.status == AccountStatusEnum.BANNED:
            return 'Проблеми входу'
        elif self.status == AccountStatusEnum.ACTIVE:
            return 'Активний'
        elif self.status == AccountStatusEnum.PAUSE:
            return 'Пауза'
        elif self.status == AccountStatusEnum.UNPAID:
            return 'Підписка'

    def get_account_type(self):
        if self.type == AccountTypeEnum.TECHNICAL:
            return 'Технічний'
        if self.type == AccountTypeEnum.PARSING:
            return 'Парсинг'
        if self.type == AccountTypeEnum.POSTING:
            return 'Постинг'
