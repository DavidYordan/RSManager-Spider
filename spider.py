# spider.py

import os
import shutil
import time
import asyncio
from collections import deque
from TikTokApi import TikTokApi

from async_tiktok_data_manager import AsyncTikTokDataManager
from custom_globals import Globals


class Spider(object):
    def __init__(self):
        self.data_manager = AsyncTikTokDataManager()
        self.api = TikTokApi()
        self.user = 'Spider'
        self.account_queue = deque()
        self.queue_set = set()

    async def main(self):
        while True:
            await self.fetch_accounts()
            await self.process_accounts()
            await asyncio.sleep(60)

    async def fetch_accounts(self):
        accounts = await self.data_manager.get_active_tiktok_accounts()
        if not accounts:
            Globals.logger.info('No active TikTok accounts found.', self.user)
            return

        def compute_priority(account):
            updated_at = account.get('updated_at')
            comments = account.get('comments', '')
            if not updated_at:
                return 0
            elif comments == '获取失败':
                return updated_at + 300
            elif comments == '账号不存在':
                return updated_at + 3600
            else:
                return updated_at

        accounts.sort(key=compute_priority)

        for account in accounts:
            account_id = account['id']
            if account_id not in self.queue_set:
                self.account_queue.append(account)
                self.queue_set.add(account_id)
                Globals.logger.info(f"Account {account['account_name']} added to queue.", self.user)

    async def process_accounts(self):
        tasks = []
        while self.account_queue:
            account = self.account_queue.popleft()
            account_id = account['id']
            self.queue_set.remove(account_id)
            task = asyncio.create_task(self.process_account(account))
            tasks.append(task)
        if tasks:
            await asyncio.gather(*tasks)

    async def process_account(self, account):
        account_id = account['id']
        account_name = account['account_name']
        Globals.logger.info(f"Processing account {account_name}.", self.user)
        try:
            user_info = await self.get_user_info(account)
            print(user_info)
            if user_info:
                user_videos = await self.get_user_videos(account)
                print(user_videos)
        except Exception as e:
            Globals.logger.error(f"Error processing account {account_name}: {e}", self.user)

    async def get_user_info(self, account):
        account_name = account['account_name']
        user_info = await self.api.user(username=account_name).info()
        return user_info

    async def get_user_videos(self, account):
        account_name = account['account_name']
        videos = []
        async for video in self.api.user(username=account_name).videos():
            video_info = video.as_dict
            videos.append(video_info)
        return videos

    async def ensure_browser(self):
        if hasattr(self.api, 'browser') and self.api.browser.is_connected():
            return
        await self.reboot_browser()

    async def reboot_browser(self):
        try:
            Globals.logger.info('Attempting to reboot the browser.', self.user)
            if hasattr(self.api, 'browser') and self.api.browser.is_connected():
                await self.api.close_sessions()
            self.terminate_playwright_processes()
            del self.api
            time.sleep(1)
            self.api = TikTokApi()
            await self.api.create_sessions(
                num_sessions=1,
                sleep_after=5,
                headless=False,
                override_browser_args=['--window-position=9999,9999']
            )
            self.minimize_chromium()
            Globals.logger.info('Browser rebooted successfully.', self.user)
        except Exception as e:
            Globals.logger.error(f'Failed to reboot the browser: {e}', self.user)

    def terminate_playwright_processes(self):
        pass

    def minimize_chromium(self):
        pass