# async_tiktok_data_manager.py

from models import AsyncSessionLocal
from models.proxy_url import ProxyUrl
from models.tiktok_relationship import TikTokRelationship
from models.tiktok_account import TikTokAccount
from models.tiktok_video_details import TikTokVideoDetails
from sqlalchemy.future import select
from typing import List

from custom_globals import Globals

class AsyncTikTokDataManager(object):
    def __init__(self):
        self.user = 'AsyncTikTokDataManager'

    async def get_active_tiktok_accounts(self) -> List[dict]:
        async with AsyncSessionLocal() as session:
            try:
                subquery = select(TikTokRelationship.tiktok_account).where(TikTokRelationship.status == True).subquery()
                query = select(
                    subquery.c.tiktok_account,
                    TikTokAccount.updated_at,
                    TikTokAccount.comments
                ).outerjoin(
                    TikTokAccount,
                    TikTokAccount.tiktok_account == subquery.c.tiktok_account
                )

                result = await session.execute(query)
                accounts = result.fetchall()

                accounts_list = []
                for account in accounts:
                    tiktok_account = account.tiktok_account
                    updated_at = account.updated_at
                    comments = account.comments
                    if updated_at is None:
                        priority_time = 0  # 不存在于 tiktok_account 表中
                    else:
                        timestamp = updated_at.timestamp()
                        if comments == '获取失败':
                            priority_time = timestamp + 300
                        elif comments == '账号不存在':
                            priority_time = timestamp + 3600
                        else:
                            priority_time = timestamp
                    accounts_list.append({
                        'account_name': tiktok_account,
                        'updated_at': updated_at,
                        'comments': comments,
                        'priority_time': priority_time
                    })
                accounts_list.sort(key=lambda x: x['priority_time'])
                return accounts_list
            except Exception as e:
                Globals.logger.error(f"Error occurred while fetching accounts: {e}", self.user)
                return []

    async def insert_or_update_tiktok_account(self, account_data: dict):
        Globals.logger.info(f"Account data: {account_data}", self.user)
        async with AsyncSessionLocal() as session:
            try:
                tiktok_account = account_data.get('tiktok_account')
                existing_account = await session.get(TikTokAccount, tiktok_account)
                if existing_account:
                    # 更新已有记录
                    for key, value in account_data.items():
                        setattr(existing_account, key, value)
                    await session.commit()
                    Globals.logger.info(f"TikTok account '{tiktok_account}' updated successfully.", self.user)
                else:
                    # 插入新记录
                    new_account = TikTokAccount(**account_data)
                    session.add(new_account)
                    await session.commit()
                    Globals.logger.info(f"TikTok account '{tiktok_account}' inserted successfully.", self.user)
            except Exception as e:
                await session.rollback()
                Globals.logger.error(f"Error occurred while inserting/updating TikTok account: {e}", self.user)

    async def insert_or_update_tiktok_video_details(self, video_data: dict):
        Globals.logger.info(f"Video data: {video_data}", self.user)
        async with AsyncSessionLocal() as session:
            try:
                tiktok_video_id = video_data.get('tiktok_video_id')
                existing_video = await session.execute(
                    select(TikTokVideoDetails).where(TikTokVideoDetails.tiktok_video_id == tiktok_video_id)
                )
                existing_video = existing_video.scalar_one_or_none()
                if existing_video:
                    # 更新已有记录
                    for key, value in video_data.items():
                        setattr(existing_video, key, value)
                    await session.commit()
                    Globals.logger.info(f"TikTok video '{tiktok_video_id}' updated successfully.", self.user)
                else:
                    # 插入新记录
                    new_video = TikTokVideoDetails(**video_data)
                    session.add(new_video)
                    await session.commit()
                    Globals.logger.info(f"TikTok video '{tiktok_video_id}' inserted successfully.", self.user)
            except Exception as e:
                await session.rollback()
                Globals.logger.error(f"Error occurred while inserting/updating TikTok video details: {e}", self.user)

    async def get_available_proxy(self):
        async with AsyncSessionLocal() as session:
            try:
                query = select(ProxyUrl).where(
                    ProxyUrl.is_using == False,
                    ProxyUrl.avg_delay > 0
                )
                proxies = (await session.execute(query)).scalars().all()
                if not proxies:
                    return None

                # 未使用过的代理，优先级最高
                unused_proxies = [p for p in proxies if p.success_count == 0 and p.fail_count == 0]
                if unused_proxies:
                    selected_proxy = min(unused_proxies, key=lambda p: p.avg_delay)
                else:
                    # 根据 success_rate 和 avg_delay 选择
                    proxies.sort(key=lambda p: (-p.success_rate, p.avg_delay))
                    selected_proxy = proxies[0]
                return {
                    'id': selected_proxy.id,
                    'current_port': selected_proxy.current_port
                }
            except Exception as e:
                Globals.logger.error(f"Error occurred while fetching available proxy: {e}", self.user)
                return None

    async def set_proxy_in_use(self, proxy_id, is_using: bool):
        async with AsyncSessionLocal() as session:
            try:
                proxy = await session.get(ProxyUrl, proxy_id)
                if proxy:
                    proxy.is_using = is_using
                    await session.commit()
            except Exception as e:
                Globals.logger.error(f"Error occurred while updating proxy is_using: {e}", self.user)

    async def increase_proxy_success(self, proxy_id):
        async with AsyncSessionLocal() as session:
            try:
                proxy = await session.get(ProxyUrl, proxy_id)
                if proxy:
                    proxy.success_count += 1
                    await session.commit()
            except Exception as e:
                Globals.logger.error(f"Error occurred while increasing proxy success count: {e}", self.user)

    async def increase_proxy_fail(self, proxy_id):
        async with AsyncSessionLocal() as session:
            try:
                proxy = await session.get(ProxyUrl, proxy_id)
                if proxy:
                    proxy.fail_count += 1
                    await session.commit()
            except Exception as e:
                Globals.logger.error(f"Error occurred while increasing proxy fail count: {e}", self.user)