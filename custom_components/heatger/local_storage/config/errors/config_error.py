"""ConfigError Exception"""
from custom_components.heatger.local_storage.consts import CLASSNAME
from custom_components.heatger.local_storage.errors.local_storage_error import LocalStorageError


class ConfigError(LocalStorageError):
    """return a Config exception"""

    def __init__(self, message: str):
        super().__init__(message, CLASSNAME)
