"""OutOfRangeError Exception"""


class OutOfRangeError(Exception):
    """return an out of range exception"""

    def __init__(self, classname: str, variable_error: str):
        super().__init__(F"{classname}: {variable_error} out of range")
