"""FileNotWritableError Exception"""
from custom_components.heatger.local_storage.errors.local_storage_error import LocalStorageError


class FileNotWritableError(LocalStorageError):
    """return a FileNotWritableError exception"""

    def __init__(self, filename: str):
        super().__init__(F"file {filename} not writable !")
