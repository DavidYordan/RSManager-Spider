# main.py

import asyncio

import models
from spider import Spider
from speed_tester import SpeedTester
from xray import Xray

async def main():
    # spider = Spider()
    # spider = Test()
    # await spider.main()
    xray_instance = Xray()
    await xray_instance.run()

    speed_tester = SpeedTester()
    asyncio.create_task(speed_tester.run())

    while True:
        await asyncio.sleep(3600)

    await models.async_engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())