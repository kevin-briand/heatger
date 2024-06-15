"""ScheduleNotValidError Exception"""
from custom_components.heatger.local_storage.config.errors.config_error import ConfigError


class ScheduleNotValidError(ConfigError):
    """return a ScheduleNotValidError exception"""

    def __init__(self):
        super().__init__("Schedule not valid !")
