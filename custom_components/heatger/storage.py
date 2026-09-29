"""Storage of the Heatger configuration and persisted states"""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .migration import is_v1_config, load_data
from .models import HeatgerConfig, PersistData

# the store keys are the ones of the version 1, the data is migrated in place
CONFIG_KEY = 'heatger-config'
PERSIST_KEY = 'heatger-persist'
# the store version is the one of the version 1 (the data has its own "version" field):
# changing it would make older releases unable to read the file
STORE_VERSION = 1


class HeatgerStorage:
    """Load / save the configuration and the persisted states"""

    def __init__(self, hass: HomeAssistant):
        self.hass = hass
        self._config_store = Store(hass, STORE_VERSION, CONFIG_KEY)
        self._persist_store = Store(hass, STORE_VERSION, PERSIST_KEY)
        self.config = HeatgerConfig()
        self.persist = PersistData()

    async def async_load(self) -> None:
        """load the data, migrate the version 1 data if needed"""
        config_raw = await self._config_store.async_load()
        persist_raw = await self._persist_store.async_load()
        if is_v1_config(config_raw):
            # keep a copy of the version 1 data (.storage/heatger-*-v1-backup), to be able to go back
            await Store(self.hass, STORE_VERSION, f'{CONFIG_KEY}-v1-backup').async_save(config_raw)
            if persist_raw is not None:
                await Store(self.hass, STORE_VERSION, f'{PERSIST_KEY}-v1-backup').async_save(persist_raw)
        self.config, self.persist, changed = load_data(config_raw, persist_raw, dt_util.now())
        if changed:
            await self.async_save_config()
            await self.async_save_persist()

    async def async_save_config(self) -> None:
        await self._config_store.async_save(self.config.to_dict())

    async def async_save_persist(self) -> None:
        await self._persist_store.async_save(self.persist.to_dict())
