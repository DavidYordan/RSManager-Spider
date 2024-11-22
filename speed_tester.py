# speed_tester.py

import asyncio
import aiohttp
from models import AsyncSessionLocal
from models.proxy_url import ProxyUrl
from models.test_speed_url import TestSpeedUrl
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func

class SpeedTester:
    def __init__(self):
        self.user = 'SpeedTester'

    async def run(self):
        await asyncio.sleep(10)
        while True:
            await self.perform_speed_tests()
            await asyncio.sleep(3600)

    async def perform_speed_tests(self):
        async with AsyncSessionLocal() as session:
            proxy_urls = await self.get_all_proxy_urls(session)
            test_speed_urls = await self.get_all_test_speed_urls(session)

        semaphore = asyncio.Semaphore(10)
        tasks = [
            self.test_speed(proxy_url, test_speed_url, semaphore)
            for proxy_url in proxy_urls
            for test_speed_url in test_speed_urls
        ]

        await asyncio.gather(*tasks)

    async def get_all_proxy_urls(self, session: AsyncSession):
        stmt = select(ProxyUrl)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def get_all_test_speed_urls(self, session: AsyncSession):
        stmt = select(TestSpeedUrl)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def test_speed(self, proxy_url: ProxyUrl, test_speed_url: TestSpeedUrl, semaphore: asyncio.Semaphore):
        async with semaphore:
            url = test_speed_url.url
            proxy = f"http://127.0.0.1:{proxy_url.current_port}"
            start_time = asyncio.get_event_loop().time()
            try:
                timeout = aiohttp.ClientTimeout(total=5)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url, proxy=proxy) as response:
                        await response.read()
                end_time = asyncio.get_event_loop().time()
                delay_ms = (end_time - start_time) * 1000

                await self.update_proxy_url_delay(proxy_url.id, delay_ms)

                await self.increment_test_speed_url_success_count(test_speed_url.id)

            except Exception as e:
                await self.increment_test_speed_url_fail_count(test_speed_url.id)

    async def update_proxy_url_delay(self, proxy_url_id: int, delay_ms: float):
        async with AsyncSessionLocal() as session:
            stmt = (
                update(ProxyUrl)
                .where(ProxyUrl.id == proxy_url_id)
                .values(
                    current_delay=delay_ms,
                    updated_at=func.now()
                )
            )
            await session.execute(stmt)
            await session.commit()

    async def increment_test_speed_url_success_count(self, test_speed_url_id: int):
        async with AsyncSessionLocal() as session:
            stmt = (
                update(TestSpeedUrl)
                .where(TestSpeedUrl.id == test_speed_url_id)
                .values(
                    success_count=TestSpeedUrl.success_count + 1
                )
            )
            await session.execute(stmt)
            await session.commit()

    async def increment_test_speed_url_fail_count(self, test_speed_url_id: int):
        async with AsyncSessionLocal() as session:
            stmt = (
                update(TestSpeedUrl)
                .where(TestSpeedUrl.id == test_speed_url_id)
                .values(
                    fail_count=TestSpeedUrl.fail_count + 1
                )
            )
            await session.execute(stmt)
            await session.commit()
