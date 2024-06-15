"""MissingArgError Exception"""
from custom_components.heatger.local_storage.consts import CLASSNAME
from custom_components.heatger.local_storage.errors.local_storage_error import LocalStorageError


class MissingArgError(LocalStorageError):
    """return a MissingArgError exception"""

    def __init__(self):
        super().__init__("Missing argument in the file", CLASSNAME)
