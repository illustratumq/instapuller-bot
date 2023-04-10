import os
import shutil
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM

from app.database.models.base import TimedBaseModel
from app.database.services.enums import PostStatusEnum


class Post(TimedBaseModel):
    post_id = sa.Column(sa.VARCHAR(15), primary_key=True, autoincrement=False, nullable=False)
    user_id = sa.Column(sa.BIGINT, nullable=True)
    customer_id = sa.Column(sa.BIGINT, nullable=True)
    executor_id = sa.Column(sa.BIGINT, nullable=True)
    status = sa.Column(ENUM(PostStatusEnum), default=PostStatusEnum.ACTIVE, nullable=False)
    caption = sa.Column(sa.VARCHAR(2200), nullable=True)
    mediacount = sa.Column(sa.INTEGER, nullable=False, default=0)
    work_id = sa.Column(sa.BIGINT, nullable=False)
    job_id = sa.Column(sa.VARCHAR(40), nullable=True)

    def delete_me(self, config) -> None:
        if self.post_id in os.listdir(config.misc.download_path):
            shutil.rmtree(Path(config.misc.download_path, self.post_id))

    def delete_my_job(self, scheduler):
        if self.job_id:
            job = scheduler.get_job(self.job_id)
            if job:
                job.remove()

    def is_am_downloaded(self, config) -> bool:
        download = False
        if self.post_id in os.listdir(config.misc.download_path):
            media_count = len(os.listdir(Path(config.misc.download_path, self.post_id)))
            if media_count != 0 and media_count == self.mediacount:
                download = True
        return download

    def get_post_files(self, config) -> list[str]:
        post_path = f'{config.misc.download_path}/{self.post_id}/'
        files = [f'{config.misc.download_path}/{self.post_id}/{file}' for file in os.listdir(post_path)
                 if file.startswith('file')]
        files.sort(key=lambda f: int(f.split('file_')[-1].split('.')[0]))
        return files

    def instagram_link(self) -> str:
        return f'<a href="https://www.instagram.com/p/{self.post_id}">{self.post_id}</a>'
