"""Logs class"""
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
        """write debug message"""
        _LOGGER.debug(F'{classname}: {message}')

    @staticmethod
    def error(classname, message):
        """write error message"""
        _LOGGER.error(F'{classname}: {message}')
