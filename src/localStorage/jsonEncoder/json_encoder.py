"""FileEncoder class"""
import datetime
from json import JSONEncoder

from src.i2c.dto.device_dto import DeviceDto
from src.shared.enum.mode import Mode
from src.shared.enum.state import State


class JsonEncoder(JSONEncoder):
    """Serialize objects"""
    def default(self, o):
        if isinstance(o, State):
            return o.value
        if isinstance(o, Mode):
            return o.value
        if isinstance(o, datetime.time):
            return o.isoformat()
        if isinstance(o, datetime.datetime):
            return o.isoformat()
        if isinstance(o, DeviceDto):
            return o.to_object()
        return o.__dict__
