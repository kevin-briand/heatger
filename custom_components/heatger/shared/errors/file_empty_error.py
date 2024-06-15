"""FileEmpty Exception"""


class FileEmptyError(Exception):
    """return a file not writable exception"""

    def __init__(self, classname: str, filename: str):
        super().__init__(F"{classname}: {filename} is empty")
