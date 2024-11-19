# async_tiktok_data_manager.py

from models import AsyncSessionLocal
from models.tiktok_relationship import TikTokRelationship
from models.tiktok_account import TikTokAccount
from models.tiktok_video_details import TikTokVideoDetails
from sqlalchemy.future import select
from typing import List

from custom_globals import Globals

class AsyncTikTokDataManager(object):
    def __init__(self):
        self.user = 'AsyncTikTokDataManager'

    async def get_active_tiktok_accounts(self) -> List[str]:
        async with AsyncSessionLocal() as session:
            try:
                result = await session.execute(
                    select(TikTokRelationship.tiktok_account).where(TikTokRelationship.status == True)
                )
                accounts = result.scalars().all()
                return accounts
            except Exception as e:
                Globals.logger.error(f"Error occurred while fetching accounts: {e}", self.user)
                return []

    async def insert_tiktok_account(self, account_data: dict):
        async with AsyncSessionLocal() as session:
            try:
                account = TikTokAccount(**account_data)
                session.add(account)
                await session.commit()
                Globals.logger.info("TikTok account inserted successfully.", self.user)
            except Exception as e:
                await session.rollback()
                Globals.logger.error(f"Error occurred while inserting TikTok account: {e}", self.user)

    async def insert_tiktok_video_details(self, video_data: dict):
        async with AsyncSessionLocal() as session:
            try:
                video_details = TikTokVideoDetails(**video_data)
                session.add(video_details)
                await session.commit()
                Globals.logger.info("TikTok video details inserted successfully.", self.user)
            except Exception as e:
                await session.rollback()
                Globals.logger.error(f"Error occurred while inserting TikTok video details: {e}", self.user)
