# main.py

import asyncio

import models
from spider import Spider
from test import Test
from xray import Xray

async def main():
    # spider = Spider()
    # spider = Test()
    # await spider.main()
    xray_instance = Xray()
    await xray_instance.run()
    await models.async_engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())