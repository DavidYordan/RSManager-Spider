# custom_globals.py

import asyncio

from custom_logger import CustomLogger

class Globals(object):
    logger = CustomLogger()
    xray_dict = {}
    lock = asyncio.Lock()
