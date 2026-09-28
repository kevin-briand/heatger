"""Zone manager class"""
from typing import Optional
import voluptuous as vol

from homeassistant.core import ServiceCall, HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util

from custom_components.heatger.const import DOMAIN
from custom_components.heatger.shared.logs.logs import Logs
from custom_components.heatger.zone.consts import ZONE, CLASSNAME
from custom_components.heatger.local_storage.config.config import Config
from custom_components.heatger.shared.enum.state import State
from custom_components.heatger.zone.frostfree import Frostfree
from custom_components.heatger.zone.zone import Zone

SERVICE_TOGGLE = 'toggle'


class ZoneManager:
    """This class is used for manage heaters zones"""

    def __init__(self, hass: HomeAssistant):
        super().__init__()
        self.zones: list[Zone] = []
        self.frostfree: Optional[Frostfree] = None
        self.hass = hass

    async def run(self) -> None:
        # frost-free is restored first, so the zones are directly created in the right state
        await self.init_frost_free()
        await self.init_zones()
        self.services_register()

    async def init_zones(self) -> None:
        """(re)create the zones from the config"""
        for zone in self.zones:
            await zone.stop_loop()
        self.zones = []
        frostfree_active = self.frostfree is not None and self.frostfree.is_active()
        for zone_id in await self.get_zone_ids():
            Logs.info("Manager", F"Init {zone_id}")
            zone = Zone(self.hass, zone_id, frostfree_active)
            await zone.async_init()
            self.zones.append(zone)

    async def get_zone_ids(self) -> list[str]:
        """return the ids of the zones in the config (zone1, zone2...) ordered by number"""
        zones = (await Config(self.hass).get_config()).zones
        return sorted((key for key in zones if key.startswith(ZONE) and key[len(ZONE):].isdigit()),
                      key=lambda key: int(key[len(ZONE):]))

    def get_zone(self, zone_id: str) -> Optional[Zone]:
        """return the zone with the given id (zone1, zone2...) or None"""
        for zone in self.zones:
            if zone.zone_id == zone_id:
                return zone
        return None

    def services_register(self):
        """Registering Services in HA"""
        if self.hass.services.has_service(DOMAIN, SERVICE_TOGGLE):
            return
        service_schema = vol.Schema({
            vol.Required("zone"): cv.positive_int,
            vol.Required("type"): vol.In(['state', 'mode']),
        })
        self.hass.services.async_register(DOMAIN, SERVICE_TOGGLE, self.processing_zone, schema=service_schema)

    def services_unregister(self):
        """Remove services from HA"""
        self.hass.services.async_remove(DOMAIN, SERVICE_TOGGLE)

    async def init_frost_free(self) -> None:
        """Frost-free initializer"""
        self.frostfree = Frostfree(self.hass, lambda: self.zones)
        await self.frostfree.async_init()

    async def processing_zone(self, call: ServiceCall) -> None:
        """processing toggle service"""
        zone_number = call.data['zone']
        toggle_type = call.data['type']
        if not 1 <= zone_number <= len(self.zones):
            raise HomeAssistantError(F'Zone {zone_number} does not exist')
        if toggle_type == 'mode':
            await self.toggle_mode(zone_number)
        else:
            await self.toggle_state(zone_number)

    async def toggle_frost_free(self, end_date: Optional[str] = None) -> None:
        """activate frost-free until end_date, deactivate it if no date or a past date is given"""
        if not end_date:
            await self.frostfree.stop()
            return
        parsed_date = dt_util.parse_datetime(end_date)
        if parsed_date is None:
            Logs.error(CLASSNAME, F'{State.FROSTFREE} - invalid date format: {end_date}')
            return
        if parsed_date.tzinfo is None:
            # no timezone given: it's a local date
            parsed_date = parsed_date.replace(tzinfo=dt_util.now().tzinfo)
        if parsed_date > dt_util.now():
            await self.frostfree.start(parsed_date)
        else:
            await self.frostfree.stop()

    async def toggle_state(self, zone_number: int) -> None:
        """switch heater state comfort<>eco"""
        await self.zones[zone_number - 1].toggle_state()

    async def toggle_mode(self, zone_number: int) -> None:
        """switch heater mode auto<>manual"""
        await self.zones[zone_number - 1].toggle_mode()

    async def get_all_data(self):
        """return the states of zones, sent to the server"""
        data = {'state': {}}
        for zone in self.zones:
            data['state'][zone.zone_id] = zone.current_state
        return data

    async def get_zones_info(self):
        """return the actual states of zones"""
        data = {}
        for zone in self.zones:
            data[zone.zone_id] = zone.get_data()
        return data

    async def get_frostfree_info(self) -> int:
        """Returns the time remaining before the end of the frost-free period, otherwise -1"""
        return self.frostfree.get_data()

    async def updated_state(self, zone_id: str, state: State):
        """Update the state for to be the same as the server"""
        Logs.info('ZONE_MANAGER', F'receipt new state: {zone_id} -> {state}')
        zone = self.get_zone(zone_id)
        if zone is None:
            Logs.error('ZONE_MANAGER', F'unknown zone received from the server: {zone_id}')
            return
        zone.current_state = state
        self.hass.states.async_set(F"{DOMAIN}.{zone_id}", state.name)

    async def stop_loop(self):
        """Stop all event loop"""
        for zone in self.zones:
            await zone.stop_loop()
        if self.frostfree:
            await self.frostfree.stop_loop()
