# main.py

import asyncio

import models
from spider import Spider
from speed_tester import SpeedTester
from xray import Xray

async def main():
    xray_instance = Xray()
    await xray_instance.run()

    speed_tester = SpeedTester()
    asyncio.create_task(speed_tester.run())
    
    spider = Spider()
    await spider.main()

    await models.async_engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())