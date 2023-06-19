import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM

from app.database.models.base import TimedBaseModel


class Error(TimedBaseModel):
    id = sa.Column(sa.BIGINT, primary_key=True, autoincrement=True, nullable=False)
    name = sa.Column(sa.VARCHAR(150), nullable=False)
    description = sa.Column(sa.VARCHAR, nullable=False)
    job_id = sa.Column(sa.VARCHAR(150), nullable=True)
    post_id = sa.Column(sa.VARCHAR, nullable=True)
    customer_id = sa.Column(sa.BIGINT, nullable=True)
    executor_id = sa.Column(sa.BIGINT, nullable=True)
    technical_id = sa.Column(sa.BIGINT, nullable=True)
    work_id = sa.Column(sa.BIGINT, nullable=True)
    proxy_id = sa.Column(sa.BIGINT, nullable=True)
    screenshot = sa.Column(sa.VARCHAR(255), nullable=True)
