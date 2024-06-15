"""LocalStorage class"""
from homeassistant.helpers.storage import Store


class LocalStorage:
    """Read/write json in store"""

    def __init__(self, hass, name: str):
        # init store
        self.store = Store(hass, 1, F'heatger-{name}')

    async def _read(self):
        """get data from store"""
        return await self.store.async_load()

    async def _write(self, data):
        """store latest data for recovery"""
        await self.store.async_save(data)
