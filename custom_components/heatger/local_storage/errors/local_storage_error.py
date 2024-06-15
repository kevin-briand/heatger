"""LocalStorageError Exception"""
from typing import Optional

from custom_components.heatger.shared.logs.logs import Logs


class LocalStorageError(Exception):
    """return a LocalStorage exception"""

    def __init__(self, message: str, classname: Optional[str] = "LocalStorage"):
        Logs.error(classname, message)
        super().__init__(F"{classname}: {message}")
