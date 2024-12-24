# custom_globals.py

import asyncio
import logging

from custom_logger import CustomLogger

class Globals(object):
    logger = CustomLogger(
        logger_name="RSManagerSpider",
        log_directory="environment/logs/mainlogs",
        level=logging.DEBUG,
    )
    xray_dict = {}
    lock = asyncio.Lock()
    session_lock = asyncio.Lock()
    get_available_proxy_lock = asyncio.Lock()
