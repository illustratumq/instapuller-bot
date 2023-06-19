import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM

from app.database.models.base import TimedBaseModel
from app.database.services.enums import FunctionStatusEnum


class Function(TimedBaseModel):
    id = sa.Column(sa.INTEGER, primary_key=True, autoincrement=True, nullable=False)
    tag = sa.Column(sa.VARCHAR(50), nullable=False, unique=True)
    name = sa.Column(sa.VARCHAR(50), nullable=False)
    description = sa.Column(sa.VARCHAR(510), nullable=False)
    status = sa.Column(ENUM(FunctionStatusEnum), nullable=False, default=FunctionStatusEnum.PAUSED)
    minutes = sa.Column(sa.INTEGER, nullable=False, default=1)
    seconds = sa.Column(sa.INTEGER, nullable=False, default=0)
    need_to_reload = sa.Column(sa.BOOLEAN, default=False, nullable=False)
    job_id = sa.Column(sa.VARCHAR(150), nullable=True)

    def if_paused_function(self):
        return self.status == FunctionStatusEnum.PAUSED

    @property
    def time(self) -> dict:
        return dict(delay=self.seconds, minutes=self.minutes)