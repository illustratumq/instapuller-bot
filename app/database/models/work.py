import sqlalchemy as sa
from sqlalchemy.orm import relationship

from app.database.services.enums import WorkModeEnum, WorkStatusEnum
from app.database.models.base import TimedBaseModel
from sqlalchemy.dialects.postgresql import ENUM


class Work(TimedBaseModel):
    work_id = sa.Column(sa.BIGINT, primary_key=True, autoincrement=True, nullable=False)
    user_id = sa.Column(sa.BIGINT, nullable=True)
    mode = sa.Column(ENUM(WorkModeEnum), nullable=True)
    customer_id = sa.Column(sa.BIGINT, nullable=True)
    executor_id = sa.Column(sa.BIGINT, nullable=True)
    status = sa.Column(ENUM(WorkStatusEnum), nullable=False, default=WorkStatusEnum.ACTIVE)
    mediacount = sa.Column(sa.BIGINT,  default=0, nullable=False)
    limit = sa.Column(sa.INTEGER, default=0, nullable=True)

