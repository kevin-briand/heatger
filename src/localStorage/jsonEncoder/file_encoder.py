"""FileEncoder class"""
import datetime
from json import JSONEncoder

from src.shared.enum.orders import Orders


class FileEncoder(JSONEncoder):
    """Serialize objects"""
    def default(self, o):
        if isinstance(o, Orders):
            return o.value
        if isinstance(o, datetime.time):
            return o.isoformat()
        if isinstance(o, datetime.datetime):
            return o.isoformat()
        return o.__dict__
