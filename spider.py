# spider.py

import time
import asyncio
from collections import deque
from TikTokApi import TikTokApi

from async_tiktok_data_manager import AsyncTikTokDataManager
from custom_globals import Globals


class Spider(object):
    def __init__(self, max_concurrent_sessions=5):
        self.data_manager = AsyncTikTokDataManager()
        self.user = 'Spider'
        self.account_queue = deque()
        self.queue_set = set()
        self.max_concurrent_sessions = max_concurrent_sessions
        self.semaphore = asyncio.Semaphore(self.max_concurrent_sessions)

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
            task = asyncio.create_task(self.process_account_semaphore(account))
            tasks.append(task)
        if tasks:
            await asyncio.gather(*tasks)

    async def process_account_semaphore(self, account):
        async with self.semaphore:
            await self.process_account(account)

    async def process_account(self, account):
        account_name = account['account_name']
        Globals.logger.info(f"Processing account {account_name}.", self.user)

        # 获取可用代理
        proxy = await self.data_manager.get_available_proxy()
        if not proxy:
            Globals.logger.error(f"No available proxy for account {account_name}.", self.user)
            return

        # 标记代理为使用中
        await self.data_manager.set_proxy_in_use(proxy['id'], True)

        # 准备代理设置
        proxy_url = f"http://127.0.0.1:{proxy['current_port']}"

        try:
            # 创建 TikTokApi 实例
            api = TikTokApi()
            # 创建带有代理的会话
            await api.create_session(proxy={'server': proxy_url})
            session_index = 0  # 因为只有一个会话

            user_info = await self.get_user_info(account, api, session_index)
            Globals.logger.info(f"User info: {user_info}", self.user)
            if user_info:
                user_videos = await self.get_user_videos(account, api, session_index)
                Globals.logger.info(f"User videos: {user_videos}", self.user)

            # 成功，增加代理的 success_count
            await self.data_manager.increase_proxy_success(proxy['id'])
        except Exception as e:
            Globals.logger.error(f"Error processing account {account_name}: {e}", self.user, exc_info=True)
            # 失败，增加代理的 fail_count
            await self.data_manager.increase_proxy_fail(proxy['id'])
        finally:
            # 关闭会话
            if api:
                await api.close_sessions()
                await api.stop_playwright()
            # 释放代理
            await self.data_manager.set_proxy_in_use(proxy['id'], False)

    async def get_user_info(self, account, api, session_index):
        account_name = account['account_name']
        user = api.user(username=account_name)
        user_info = await user.info(session_index=session_index)
        return user_info

    async def get_user_videos(self, account, api, session_index):
        account_name = account['account_name']
        videos = []
        async for video in api.user(username=account_name).videos(session_index=session_index):
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
            )
            Globals.logger.info('Browser rebooted successfully.', self.user)
        except Exception as e:
            Globals.logger.error(f'Failed to reboot the browser: {e}', self.user)

    def terminate_playwright_processes(self):
        pass
