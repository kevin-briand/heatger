"""Logs class"""
from datetime import datetime

import logging

_LOGGER = logging.getLogger(__name__)


class Logs:
    """Write messages in logs file"""

    @staticmethod
    def info(classname, message):
        """write info message"""
        _LOGGER.info(F'{classname}: {message}')

    @staticmethod
    def debug(classname, message):
        """write debug message (console only)"""
        current_date_str = datetime.now().strftime('%d/%m/%Y %H:%M:%S - ')
        _LOGGER.error(F'{current_date_str} - {classname}: {message}')

    @staticmethod
    def error(classname, message):
        """write error message"""
        _LOGGER.error(F' - {classname}: {message}')
