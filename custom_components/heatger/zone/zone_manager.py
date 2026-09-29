"""Zone manager class"""
from __future__ import annotations

import logging
from typing import Optional

from homeassistant.core import HomeAssistant

from ..actuators import create_actuator
from ..actuators.pilot_wire import PilotWireActuator
from ..const import DOMAIN
from ..models import HeatgerError
from ..season import SeasonManager
from ..shared.enum.season import Season
from ..shared.enum.state import State
from ..storage import HeatgerStorage
from .zone import Zone

_LOGGER = logging.getLogger(__name__)


class ZoneManager:
    """Create the zones (enabled ones) and their actuators, dispatch the season changes"""

    def __init__(self, hass: HomeAssistant, storage: HeatgerStorage, season: SeasonManager):
        self.hass = hass
        self.storage = storage
        self.season = season
        self.zones: list[Zone] = []
        self._unsub_season = None

    async def async_start(self) -> None:
        number = 0
        for config in self.storage.config.zones:
            if not config.enabled:
                continue
            number += 1
            actuators = [create_actuator(self.hass, self.storage, actuator) for actuator in config.actuators]
            zone = Zone(self.hass, self.storage, config, self.season, actuators, number)
            self.zones.append(zone)
        for zone in self.zones:
            await zone.async_start()
        self._unsub_season = self.season.season_listeners.add(self._on_season_changed)

    async def async_stop(self) -> None:
        if self._unsub_season:
            self._unsub_season()
            self._unsub_season = None
        for zone in self.zones:
            await zone.async_stop()

    async def _on_season_changed(self) -> None:
        for zone in self.zones:
            await zone.on_season_changed()

    # ---- lookup

    def get_zone(self, zone_id: str) -> Zone:
        """zone by id, by name or by number"""
        for zone in self.zones:
            if zone_id in (zone.zone_id, zone.name, str(zone.number)):
                return zone
        raise HeatgerError(f'Zone {zone_id} does not exist or is disabled')

    def get_zone_by_number(self, number: int) -> Zone:
        if not 1 <= number <= len(self.zones):
            raise HeatgerError(f'Zone {number} does not exist')
        return self.zones[number - 1]

    def pilot_wires(self) -> list[PilotWireActuator]:
        return [actuator for zone in self.zones for actuator in zone.actuators
                if isinstance(actuator, PilotWireActuator)]

    def find_actuator(self, actuator_id: str):
        for zone in self.zones:
            for actuator in zone.actuators:
                if actuator.id == actuator_id:
                    return zone, actuator
        return None, None

    # ---- heatger server

    async def get_all_data(self) -> dict:
        """orders of all the pilot wire outputs, sent to the server"""
        return {'state': {actuator.output: actuator.last_order for actuator in self.pilot_wires()
                          if actuator.last_order is not None}}

    async def updated_state(self, output: str, state: State) -> None:
        """the server sent the state of an output"""
        _LOGGER.debug('receipt new state: %s -> %s', output, state)
        found = False
        for actuator in self.pilot_wires():
            if actuator.output == output:
                actuator.server_state(state)
                found = True
        if not found:
            _LOGGER.warning('Unknown output received from the server: %s', output)
            return
        # raw state kept for the compatibility with the version 1 (heatger.zone1...)
        self.hass.states.async_set(f"{DOMAIN}.{output}", state.name)

    # ---- data

    async def get_zones_info(self) -> dict:
        return {zone.zone_id: zone.get_data() for zone in self.zones}

    async def get_frostfree_info(self) -> int:
        """compatibility with the version 1 of the card: remaining time of the season stop, else -1"""
        if self.season.current != Season.STOP:
            return -1
        return self.season.remaining_seconds()

    def zone_or_none(self, zone_id: str) -> Optional[Zone]:
        try:
            return self.get_zone(zone_id)
        except HeatgerError:
            return None
