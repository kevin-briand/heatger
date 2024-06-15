"""FileEncoder class"""
import datetime
from json import JSONEncoder

from custom_components.heatger.shared.enum.mode import Mode
from custom_components.heatger.shared.enum.state import State


class JsonEncoder(JSONEncoder):
    """Serialize objects"""
    def default(self, o) -> str:
        if isinstance(o, State):
            return o.value
        if isinstance(o, Mode):
            return o.value
        if isinstance(o, datetime.time):
            return o.isoformat()
        if isinstance(o, datetime.datetime):
            return o.isoformat()
        return super().default(o)
