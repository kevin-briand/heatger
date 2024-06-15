"""Zone manager class"""
from datetime import datetime
from typing import Optional
import voluptuous as vol

from homeassistant.core import ServiceCall, HomeAssistant
from homeassistant.helpers import config_validation as cv

from custom_components.heatger.const import DOMAIN
from custom_components.heatger.shared.logs.logs import Logs
from custom_components.heatger.zone.consts import ZONE, CLASSNAME
from custom_components.heatger.local_storage.config.config import Config
from custom_components.heatger.shared.enum.state import State
from custom_components.heatger.shared.timer.timer import Timer
from custom_components.heatger.zone.frostfree import Frostfree
from custom_components.heatger.zone.zone import Zone


class ZoneManager:
    """This class is used for manage heaters zones"""

    def __init__(self, hass: HomeAssistant):
        super().__init__()
        self.zones: list[Zone] = []
        self.frostfree: Optional[Frostfree] = None
        self.current_datas = {}
        self.update_datas_timer = Timer()
        self.hass = hass

    async def run(self) -> None:
        await self.init_zones()
        await self.init_frost_free()
        await self.services_register()
        await self.get_all_data()

    async def init_zones(self) -> None:
        """zones initializer"""
        for zone in self.zones:
            await zone.stop_loop()
        self.zones = []
        try:
            await self.init_zones_from_config_file()
        except KeyError:
            Logs.info('INIT', len(self.zones))
            pass

    async def init_zones_from_config_file(self) -> None:
        """Initialize zones from config file"""
        i = 1
        zones = (await Config(self.hass).get_config()).zones
        while zones[F"{ZONE}{i}"] is not None:
            Logs.info("Manager", F"Init Zone {i}")
            zone = Zone(self.hass, i)
            await zone.async_init()
            self.zones.append(zone)
            i += 1

    async def services_register(self):
        """Registering Services in HA"""
        service_schema = vol.Schema({
            vol.Required("zone"): cv.positive_int,
            vol.Required("type"): cv.string,
        })
        try:
            self.hass.services.async_register(DOMAIN, 'toggle', self.processing_zone, schema=service_schema)
        except Exception as e:
            Logs.error('ERT', "Error registering service: " + e.__str__())

    async def init_frost_free(self) -> None:
        """Frost-free initializer"""
        self.frostfree = Frostfree(self.hass, self.zones)
        await self.frostfree.async_init()

    async def processing_zone(self, call: ServiceCall) -> bool:
        """processing zone mqtt message"""
        data = call.data
        zone = data['zone']
        toggle_type = data['type']
        if not toggle_type or not zone or not 0 < zone < 3:
            return False
        if toggle_type not in ['state', 'mode']:
            return False
        if toggle_type == 'mode':
            await self.toggle_mode(zone)
        elif toggle_type == 'state':
            await self.toggle_state(zone)
        return True

    async def toggle_frost_free(self, end_date: str = None) -> None:
        """activate frost-free"""
        Logs.info('TEST', end_date)
        if not end_date:
            await self.frostfree.stop()
            return
        if end_date == '':
            Logs.error(CLASSNAME, F'{State.FROSTFREE} - empty data')
            return
        try:
            end_date = datetime.strptime(end_date, '%Y-%m-%dT%H:%M:%S.%fZ')
        except ValueError:
            Logs.error(CLASSNAME, F'{State.FROSTFREE} - invalid date format')
            return
        if end_date > datetime.now():
            await self.frostfree.start(end_date)
        else:
            await self.frostfree.stop()

    async def toggle_state(self, zone_number: int) -> None:
        """switch heater state comfort<>eco"""
        await self.zones[zone_number - 1].toggle_state()

    async def toggle_mode(self, zone_number: int) -> None:
        """switch heater state comfort<>eco"""
        await self.zones[zone_number - 1].toggle_mode()

    async def get_all_data(self):
        data = {'state': {}}
        for zone in self.zones:
            data['state'][zone.zone_id] = zone.current_state
        Logs.info('INFO', data)
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

    async def updated_state(self, zone: str, state: State):
        """Update the state for to be the same as the server"""
        Logs.info('ZONE_MANAGER', F'receipt new state: {zone} -> {state}')
        self.zones[await Zone.get_zone_number(self.hass, zone) - 1].current_state = state
        self.hass.states.async_set(F"{DOMAIN}.{zone}", state.name)

    async def stop_loop(self):
        """Stop all event loop"""
        for zone in self.zones:
            await zone.stop_loop()
        await self.frostfree.stop_loop()
