from app.database.services.db_ctx import BaseRepo

from app.database.models import *
from app.database.services.enums import *


class UserRepo(BaseRepo[User]):
    model = User

    async def get_user(self, user_id: int) -> User:
        return await self.get_one(self.model.user_id == user_id)

    async def update_user(self, user_id: int, **kwargs) -> None:
        return await self.update(self.model.user_id == user_id, **kwargs)

    async def get_users_status(self, status: UserStatusEnum) -> list[User]:
        return await self.get_all(self.model.status == status)
    

class AccountRepo(BaseRepo[Account]):
    model = Account

    async def get_account(self, account_id) -> Account:
        return await self.get_one(self.model.account_id == account_id)

    async def update_account(self, account_id, **kwargs) -> None:
        return await self.update(self.model.account_id == account_id, **kwargs)

    async def get_accounts_type(self, account_type: AccountTypeEnum) -> list[Account]:
        return await self.get_all(self.model.type == account_type)

    async def get_accounts_status(self, account_type: AccountTypeEnum, status: AccountStatusEnum) -> list[Account]:
        return await self.get_all(self.model.type == account_type, self.model.status == status)

    async def get_accounts_by_user(self, user_id: int, account_type: AccountTypeEnum) -> list[Account]:
        return await self.get_all(self.model.user_id == user_id, self.model.type == account_type)

    async def get_account_by_username(self, username: str, account_type: AccountTypeEnum) -> Account:
        return await self.get_one(self.model.username == username, self.model.type == account_type)

    async def get_free_technicals(self) -> list[Account]:
        accounts = await self.get_all(
            self.model.type == AccountTypeEnum.TECHNICAL,
            self.model.status == AccountStatusEnum.ACTIVE,
            self.model.free_action > 0
        )
        if accounts:
            accounts.sort(key=lambda technical: technical.updated_at)
            return accounts
        else:
            return []

    async def delete_account(self, account_id: int):
        return await self.delete(self.model.account_id == account_id)


class PostRepo(BaseRepo[Post]):
    model = Post

    async def get_post(self, post_id: str):
        return await self.get_one(self.model.post_id == post_id)

    async def update_post(self, post_id: str, **kwargs) -> None:
        return await self.update(self.model.post_id == post_id, **kwargs)

    async def get_posts_status(self, status: PostStatusEnum) -> list[Post]:
        return await self.get_all(self.model.status == status)

    async def get_posts_executor(self, account_id: int, status: PostStatusEnum) -> list[Post]:
        return await self.get_all(self.model.executor_id == account_id, self.model.status == status)

    async def get_posts_customer(self, account_id: int, status: PostStatusEnum) -> list[Post]:
        return await self.get_all(self.model.customer_id == account_id, self.model.status == status)

    async def get_posts_account(self, account_id: int) -> list[Post]:
        return await self.get_all(self.model.customer_id == account_id)

    async def get_post_work(self, work_id: int) -> list[Post]:
        return await self.get_all(self.model.work_id == work_id)

    async def if_post_exist(self, customer_id: int, post_id: str):
        return bool(await self.get_one(self.model.customer_id == customer_id, self.model.post_id == post_id))

    async def delete_post(self, post_id: str):
        await self.delete(self.model.post_id == post_id)


class WorkRepo(BaseRepo[Work]):
    model = Work

    async def get_work(self, work_id: int) -> Work:
        return await self.get_one(self.model.work_id == work_id)

    async def update_work(self, work_id: int, **kwargs):
        return await self.update(self.model.work_id == work_id, **kwargs)

    async def get_work_customer(self, account_id: int):
        return await self.get_all(self.model.customer_id == account_id)

    async def get_work_executor(self, account_id: int):
        return await self.get_all(self.model.executor_id == account_id)

    async def get_custom_work(self, customer_id: int, executor_id: int, mode: WorkModeEnum):
        return await self.get_all(self.model.customer_id == customer_id,
                                  self.model.executor_id == executor_id,
                                  self.model.mode == mode)

    async def get_work_status(self, status: WorkStatusEnum) -> list[Work]:
        return await self.get_all(self.model.status == status)

    async def get_work_mode(self, mode: WorkModeEnum) -> list[Work]:
        return await self.get_all(self.model.mode == mode)

    async def delete_work(self, work_id: int):
        return await self.delete(self.model.work_id == work_id)


__all__ = (
    'AccountRepo', 'UserRepo', 'PostRepo', 'WorkRepo'
)
