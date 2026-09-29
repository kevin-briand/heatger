"""Thermostat actuator: any climate entity of Home Assistant (air conditioner, heat pump, connected radiator...)"""
from __future__ import annotations

import logging
from collections import deque
from typing import Any, Optional

from homeassistant.const import ATTR_ENTITY_ID, ATTR_TEMPERATURE, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Context, Event, HomeAssistant, State as HAState
from homeassistant.helpers.event import async_track_state_change_event

from ..const import SETPOINT_OFF, SETPOINTS_COOL, SETPOINTS_HEAT
from ..models import ActuatorConfig, Setpoints
from ..shared.enum.season import Season
from ..shared.enum.state import State
from ..storage import HeatgerStorage
from .base import Actuator

_LOGGER = logging.getLogger(__name__)

CLIMATE_DOMAIN = 'climate'
HVAC_OFF = 'off'
HVAC_HEAT = 'heat'
HVAC_COOL = 'cool'
ATTR_HVAC_MODE = 'hvac_mode'
ATTR_HVAC_MODES = 'hvac_modes'
ATTR_PRESET_MODE = 'preset_mode'
ATTR_PRESET_MODES = 'preset_modes'
ATTR_MIN_TEMP = 'min_temp'
ATTR_MAX_TEMP = 'max_temp'
NOT_AVAILABLE = (STATE_UNAVAILABLE, STATE_UNKNOWN)

# season -> (setpoints key, hvac mode)
SEASON_MODES = {
    Season.HEATING: (SETPOINTS_HEAT, HVAC_HEAT),
    Season.COOLING: (SETPOINTS_COOL, HVAC_COOL),
}


def capabilities_of(state: Optional[HAState]) -> Optional[dict]:
    """capabilities of a climate entity, None if the entity is not available"""
    if state is None or state.state in NOT_AVAILABLE:
        return None
    attributes = state.attributes
    return {
        'hvac_modes': [str(mode) for mode in attributes.get(ATTR_HVAC_MODES) or []],
        'preset_modes': list(attributes.get(ATTR_PRESET_MODES) or []),
        'min_temp': attributes.get(ATTR_MIN_TEMP),
        'max_temp': attributes.get(ATTR_MAX_TEMP),
    }


class ClimateActuator(Actuator):
    """Drive a climate entity with the setpoints of the season.

    - controlled during a season only if the device supports it (hvac_modes) and setpoints are set for it
    - out of season: turned off once when the season starts, then never touched
    - a change made outside of heatger (remote, dashboard, automation) is respected until the next change of
      state of the zone or of season
    - device unavailable: the order is applied as soon as it's back
    """

    def __init__(self, hass: HomeAssistant, storage: HeatgerStorage, config: ActuatorConfig):
        super().__init__(hass, storage, config)
        self.manual = False
        self.pending = False
        self.expected: Optional[dict[str, Any]] = None
        self._own_contexts: deque[str] = deque(maxlen=30)
        self._unsub = None

    @property
    def entity_id(self) -> str:
        return self.config.entity_id or ''

    async def async_start(self) -> None:
        self._unsub = async_track_state_change_event(self.hass, [self.entity_id], self._on_state_event)

    async def async_stop(self) -> None:
        if self._unsub:
            self._unsub()
            self._unsub = None

    def capabilities(self) -> Optional[dict]:
        return capabilities_of(self.hass.states.get(self.entity_id))

    def setpoints_for(self, season: Season) -> Optional[Setpoints]:
        if season not in SEASON_MODES:
            return None
        return self.config.setpoints(SEASON_MODES[season][0])

    def is_controlled(self, season: Season, capabilities: Optional[dict]) -> bool:
        """controlled during the season: setpoints are set, and the device supports it (if known)"""
        if self.setpoints_for(season) is None:
            return False
        if capabilities is None:
            return True
        return SEASON_MODES[season][1] in capabilities['hvac_modes']

    async def apply(self, state: State, season: Season, new_slot: bool) -> None:
        self.last = (state, season)
        if new_slot and self.manual:
            self.manual = False
            await self.listeners.notify()
        capabilities = self.capabilities()

        if not self.is_controlled(season, capabilities):
            self.expected = None
            await self._turn_off_once(season, capabilities)
            return

        persist = self.storage.persist
        changed = persist.actuators_off.pop(self.id, None) is not None
        if self.id not in persist.known_actuators:
            persist.known_actuators.append(self.id)
            changed = True
        if changed:
            await self.storage.async_save_persist()
        if self.manual:
            return
        if capabilities is None:
            self.pending = True
            _LOGGER.info('%s unavailable, the order will be sent when it is back', self.entity_id)
            return
        self.pending = False
        await self._send(self._desired(state, season, capabilities))

    async def _turn_off_once(self, season: Season, capabilities: Optional[dict]) -> None:
        """out of season: turn off the device once, then leave it to the user"""
        persist = self.storage.persist
        if self.id not in persist.known_actuators:
            # new actuator (just configured): left as is until the next change of season
            persist.known_actuators.append(self.id)
            persist.actuators_off[self.id] = season.value
            await self.storage.async_save_persist()
        if persist.actuators_off.get(self.id) == season.value:
            self.pending = False
            return
        if capabilities is None:
            self.pending = True
            return
        self.pending = False
        _LOGGER.info('%s out of season (%s): turned off once, then not controlled', self.entity_id, season.value)
        await self._send({ATTR_HVAC_MODE: HVAC_OFF})
        self.storage.persist.actuators_off[self.id] = season.value
        await self.storage.async_save_persist()

    def _desired(self, state: State, season: Season, capabilities: dict) -> dict[str, Any]:
        """state wanted for the device"""
        setpoints = self.setpoints_for(season)
        setpoint = setpoints.get(state)
        hvac_mode = SEASON_MODES[season][1]
        if setpoint == SETPOINT_OFF:
            return {ATTR_HVAC_MODE: HVAC_OFF}
        if isinstance(setpoint, dict):
            return {ATTR_HVAC_MODE: hvac_mode, ATTR_PRESET_MODE: setpoint['preset']}
        temperature = float(setpoint)
        if capabilities.get('min_temp') is not None:
            temperature = max(temperature, float(capabilities['min_temp']))
        if capabilities.get('max_temp') is not None:
            temperature = min(temperature, float(capabilities['max_temp']))
        return {ATTR_HVAC_MODE: hvac_mode, ATTR_TEMPERATURE: temperature}

    @staticmethod
    def matches(state: Optional[HAState], desired: dict[str, Any]) -> bool:
        """True if the device is in the desired state"""
        if state is None or state.state != desired[ATTR_HVAC_MODE]:
            return False
        if ATTR_TEMPERATURE in desired:
            current = state.attributes.get(ATTR_TEMPERATURE)
            try:
                if current is None or abs(float(current) - desired[ATTR_TEMPERATURE]) > 0.05:
                    return False
            except (TypeError, ValueError):
                return False
        if ATTR_PRESET_MODE in desired and state.attributes.get(ATTR_PRESET_MODE) != desired[ATTR_PRESET_MODE]:
            return False
        return True

    async def _call(self, service: str, data: dict) -> None:
        context = Context()
        self._own_contexts.append(context.id)
        await self.hass.services.async_call(CLIMATE_DOMAIN, service, {ATTR_ENTITY_ID: self.entity_id, **data},
                                            blocking=True, context=context)

    async def _send(self, desired: dict[str, Any]) -> None:
        self.expected = desired
        if self.matches(self.hass.states.get(self.entity_id), desired):
            return
        try:
            if desired[ATTR_HVAC_MODE] == HVAC_OFF:
                await self._call('set_hvac_mode', {ATTR_HVAC_MODE: HVAC_OFF})
            elif ATTR_TEMPERATURE in desired:
                await self._call('set_temperature', {ATTR_TEMPERATURE: desired[ATTR_TEMPERATURE],
                                                     ATTR_HVAC_MODE: desired[ATTR_HVAC_MODE]})
            else:
                await self._call('set_hvac_mode', {ATTR_HVAC_MODE: desired[ATTR_HVAC_MODE]})
                await self._call('set_preset_mode', {ATTR_PRESET_MODE: desired[ATTR_PRESET_MODE]})
            _LOGGER.debug('%s set to %s', self.entity_id, desired)
        except Exception as e:  # pylint: disable=broad-except
            _LOGGER.error('Failure to drive %s (%s): %s', self.entity_id, desired, e)

    async def _on_state_event(self, event: Event) -> None:
        new_state: Optional[HAState] = event.data.get('new_state')
        old_state: Optional[HAState] = event.data.get('old_state')
        if new_state is None or new_state.state in NOT_AVAILABLE:
            return
        if old_state is None or old_state.state in NOT_AVAILABLE:
            # back online
            if self.pending:
                _LOGGER.info('%s is back, applying the pending order', self.entity_id)
                await self.reapply()
            return
        context = event.context
        if context.id in self._own_contexts or (context.parent_id and context.parent_id in self._own_contexts):
            return
        if self.expected is None or self.manual:
            return
        if not self.matches(new_state, self.expected):
            self.manual = True
            _LOGGER.info('%s changed outside of heatger: respected until the next change of state', self.entity_id)
            await self.listeners.notify()

    def get_info(self) -> dict:
        capabilities = self.capabilities()
        season = self.last[1] if self.last else None
        return {**super().get_info(), 'entity_id': self.entity_id, 'manual': self.manual,
                'available': capabilities is not None,
                'controlled': season is not None and self.is_controlled(season, capabilities)}
