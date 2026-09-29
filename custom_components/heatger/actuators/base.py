"""Base class of the actuators"""
from __future__ import annotations

from typing import Optional

from homeassistant.core import HomeAssistant

from ..models import ActuatorConfig
from ..shared.enum.season import Season
from ..shared.enum.state import State
from ..shared.listeners import Listeners
from ..storage import HeatgerStorage


class Actuator:
    """An actuator receives the state of its zone (comfort / eco) and the season, and drives a device"""

    def __init__(self, hass: HomeAssistant, storage: HeatgerStorage, config: ActuatorConfig):
        self.hass = hass
        self.storage = storage
        self.config = config
        self.listeners = Listeners()
        # last state/season applied, used to apply again (new setpoint, device back online)
        self.last: Optional[tuple[State, Season]] = None

    @property
    def id(self) -> str:
        return self.config.id

    async def async_start(self) -> None:
        """start listening what is needed"""

    async def async_stop(self) -> None:
        """stop listening"""

    async def apply(self, state: State, season: Season, new_slot: bool) -> None:
        """apply the state of the zone.

        :param new_slot: True when the state of the zone or the season changed (a manual setting of the
            device is respected until then)
        """
        raise NotImplementedError

    async def reapply(self) -> None:
        """apply again the last state (the config changed)"""
        if self.last is not None:
            await self.apply(self.last[0], self.last[1], False)

    def get_info(self) -> dict:
        """status of the actuator, for the panel and the entities"""
        return {'id': self.id, 'type': self.config.type, 'name': self.config.name}
