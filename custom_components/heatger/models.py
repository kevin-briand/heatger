"""Data models of the Heatger configuration and of its persisted states.

The models are stored as plain json (dict/list) in the Home Assistant stores, every model
has a from_dict / to_dict pair so the stored format is explicit.
"""
from __future__ import annotations

import datetime
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional, Union

from homeassistant.util import dt as dt_util

from .const import (ACTUATOR_CLIMATE, ACTUATOR_PILOT_WIRE, PROGRAMS, SETPOINT_OFF,
                    SETPOINTS_COOL, SETPOINTS_HEAT)
from .shared.enum.mode import Mode
from .shared.enum.season import Season
from .shared.enum.state import State

CONFIG_VERSION = 2
PERSIST_VERSION = 2

# a setpoint is a temperature, "off", or a preset of the device: {"preset": "eco"}
Setpoint = Union[float, str, dict]


class HeatgerError(Exception):
    """Error of the Heatger configuration (invalid data, unknown zone...)"""


def new_id() -> str:
    """return a new stable identifier"""
    return uuid.uuid4().hex[:12]


def datetime_to_str(value: Optional[datetime.datetime]) -> Optional[str]:
    """serialize an aware datetime"""
    return value.isoformat() if value else None


def str_to_datetime(value: Optional[str]) -> Optional[datetime.datetime]:
    """parse a datetime, a naive one is considered as local time"""
    if not value:
        return None
    result = dt_util.parse_datetime(value)
    if result is None:
        return None
    if result.tzinfo is None:
        result = result.replace(tzinfo=dt_util.now().tzinfo)
    return result


@dataclass
class Schedule:
    """A change of state in a weekly program"""
    day: int  # 0 = monday
    hour: datetime.time
    state: State

    def to_value(self) -> int:
        """return a sortable value, the bigger it is, the closer it is to the end of the week"""
        return self.day * 10000 + self.hour.hour * 100 + self.hour.minute

    def __eq__(self, other: object) -> bool:
        # two schedules at the same time are the same schedule, whatever the state
        return isinstance(other, Schedule) and self.to_value() == other.to_value()

    def is_valid(self) -> bool:
        """return True if the schedule is valid"""
        return 0 <= self.day <= 6 and self.state in (State.COMFORT, State.ECO)

    @staticmethod
    def from_dict(data: dict) -> 'Schedule':
        """parse {"day": 0, "hour": "07:30", "state": 0}, hour can be "07:30:00" """
        hour, minute = str(data['hour']).split(':')[:2]
        return Schedule(int(data['day']), datetime.time(int(hour), int(minute)), State(int(data['state'])))

    def to_dict(self) -> dict:
        return {'day': self.day, 'hour': self.hour.strftime('%H:%M'), 'state': self.state.value}


def sort_schedules(schedules: list[Schedule]) -> list[Schedule]:
    """return the schedules sorted by time in the week"""
    return sorted(schedules, key=lambda s: s.to_value())


def parse_setpoint(value: Any) -> Setpoint:
    """validate a setpoint: a temperature, "off" or {"preset": "<name>"}"""
    if value == SETPOINT_OFF:
        return SETPOINT_OFF
    if isinstance(value, dict):
        preset = value.get('preset')
        if not isinstance(preset, str) or not preset:
            raise HeatgerError(f'Invalid preset setpoint: {value}')
        return {'preset': preset}
    if isinstance(value, bool):
        raise HeatgerError(f'Invalid setpoint: {value}')
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise HeatgerError(f'Invalid setpoint: {value}') from exc


@dataclass
class Setpoints:
    """Setpoints of a climate actuator for one season"""
    comfort: Setpoint
    eco: Setpoint

    def get(self, state: State) -> Setpoint:
        return self.comfort if state == State.COMFORT else self.eco

    @staticmethod
    def from_dict(data: Optional[dict]) -> Optional['Setpoints']:
        if not data:
            return None
        return Setpoints(parse_setpoint(data['comfort']), parse_setpoint(data['eco']))

    def to_dict(self) -> dict:
        return {'comfort': self.comfort, 'eco': self.eco}


@dataclass
class ActuatorConfig:
    """An actuator of a zone: a pilot wire output of the heatger server or a climate entity"""
    id: str
    type: str
    name: str = ''
    # pilot wire
    output: Optional[str] = None
    # climate
    entity_id: Optional[str] = None
    heat: Optional[Setpoints] = None
    cool: Optional[Setpoints] = None

    def setpoints(self, key: str) -> Optional[Setpoints]:
        return self.heat if key == SETPOINTS_HEAT else self.cool

    def set_setpoints(self, key: str, value: Optional[Setpoints]) -> None:
        if key == SETPOINTS_HEAT:
            self.heat = value
        else:
            self.cool = value

    @staticmethod
    def from_dict(data: dict) -> 'ActuatorConfig':
        actuator_type = data.get('type')
        if actuator_type == ACTUATOR_PILOT_WIRE:
            if not data.get('output'):
                raise HeatgerError('A pilot wire actuator needs an output')
            return ActuatorConfig(data.get('id') or new_id(), actuator_type, data.get('name', ''),
                                  output=str(data['output']))
        if actuator_type == ACTUATOR_CLIMATE:
            entity_id = data.get('entity_id')
            if not entity_id or not str(entity_id).startswith('climate.'):
                raise HeatgerError('A thermostat actuator needs a climate entity')
            return ActuatorConfig(data.get('id') or new_id(), actuator_type, data.get('name', ''),
                                  entity_id=entity_id,
                                  heat=Setpoints.from_dict(data.get(SETPOINTS_HEAT)),
                                  cool=Setpoints.from_dict(data.get(SETPOINTS_COOL)))
        raise HeatgerError(f'Unknown actuator type: {actuator_type}')

    def to_dict(self) -> dict:
        result: dict = {'id': self.id, 'type': self.type, 'name': self.name}
        if self.type == ACTUATOR_PILOT_WIRE:
            result['output'] = self.output
        else:
            result['entity_id'] = self.entity_id
            result[SETPOINTS_HEAT] = self.heat.to_dict() if self.heat else None
            result[SETPOINTS_COOL] = self.cool.to_dict() if self.cool else None
        return result


@dataclass
class ZoneConfig:
    """A zone: programs, actuators"""
    id: str
    name: str
    enabled: bool = True
    programs: dict[str, list[Schedule]] = field(default_factory=lambda: {key: [] for key in PROGRAMS})
    actuators: list[ActuatorConfig] = field(default_factory=list)
    temperature_sensor: Optional[str] = None

    @staticmethod
    def from_dict(data: dict) -> 'ZoneConfig':
        programs = data.get('programs') or {}
        return ZoneConfig(
            id=data.get('id') or new_id(),
            name=str(data.get('name', '')).strip(),
            enabled=bool(data.get('enabled', True)),
            programs={key: sort_schedules([Schedule.from_dict(s) for s in programs.get(key) or []])
                      for key in PROGRAMS},
            actuators=[ActuatorConfig.from_dict(a) for a in data.get('actuators') or []],
            temperature_sensor=data.get('temperature_sensor') or None,
        )

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'enabled': self.enabled,
            'programs': {key: [s.to_dict() for s in self.programs.get(key, [])] for key in PROGRAMS},
            'actuators': [a.to_dict() for a in self.actuators],
            'temperature_sensor': self.temperature_sensor,
        }


@dataclass
class HeatgerConfig:
    """The whole configuration (store heatger-config)"""
    zones: list[ZoneConfig] = field(default_factory=list)
    users: list[str] = field(default_factory=list)

    def get_zone(self, zone_id: str) -> ZoneConfig:
        for zone in self.zones:
            if zone.id == zone_id:
                return zone
        raise HeatgerError(f'Zone {zone_id} not found')

    def find_actuator(self, actuator_id: str) -> tuple[ZoneConfig, ActuatorConfig]:
        for zone in self.zones:
            for actuator in zone.actuators:
                if actuator.id == actuator_id:
                    return zone, actuator
        raise HeatgerError(f'Actuator {actuator_id} not found')

    @staticmethod
    def from_dict(data: dict) -> 'HeatgerConfig':
        return HeatgerConfig(zones=[ZoneConfig.from_dict(z) for z in data.get('zones') or []],
                             users=list(data.get('users') or []))

    def to_dict(self) -> dict:
        return {'version': CONFIG_VERSION,
                'zones': [z.to_dict() for z in self.zones],
                'users': self.users}


@dataclass
class ZonePersist:
    """Persisted state of a zone"""
    state: State = State.ECO
    mode: Mode = Mode.AUTO
    # temporary override of the program: state + end date (None = until the next change of the program)
    override_state: Optional[State] = None
    override_until: Optional[datetime.datetime] = None

    @staticmethod
    def from_dict(data: dict) -> 'ZonePersist':
        state = State(int(data.get('state', State.ECO.value)))
        if state == State.FROSTFREE:
            state = State.ECO
        override = data.get('override') or None
        return ZonePersist(
            state=state,
            mode=Mode(int(data.get('mode', Mode.AUTO.value))),
            override_state=State(int(override['state'])) if override else None,
            override_until=str_to_datetime(override.get('until')) if override else None,
        )

    def to_dict(self) -> dict:
        return {
            'state': self.state.value,
            'mode': self.mode.value,
            'override': {'state': self.override_state.value,
                         'until': datetime_to_str(self.override_until)} if self.override_state else None,
        }


@dataclass
class SeasonPersist:
    """Persisted season: current one, and optionally the date it ends and the season that follows"""
    current: Season = Season.HEATING
    until: Optional[datetime.datetime] = None
    next: Season = Season.HEATING

    @staticmethod
    def from_dict(data: Optional[dict]) -> 'SeasonPersist':
        if not data:
            return SeasonPersist()
        return SeasonPersist(Season(data.get('current', Season.HEATING.value)),
                             str_to_datetime(data.get('until')),
                             Season(data.get('next', Season.HEATING.value)))

    def to_dict(self) -> dict:
        return {'current': self.current.value, 'until': datetime_to_str(self.until), 'next': self.next.value}


@dataclass
class PersistData:
    """The persisted states (store heatger-persist)"""
    season: SeasonPersist = field(default_factory=SeasonPersist)
    zones: dict[str, ZonePersist] = field(default_factory=dict)
    # actuator id -> season during which the actuator was already turned off (out of season)
    actuators_off: dict[str, str] = field(default_factory=dict)
    # actuators already started once (a new actuator is not turned off: it's left as is until the next season)
    known_actuators: list[str] = field(default_factory=list)

    def zone(self, zone_id: str) -> ZonePersist:
        """return the persisted state of a zone, created if missing"""
        if zone_id not in self.zones:
            self.zones[zone_id] = ZonePersist()
        return self.zones[zone_id]

    @staticmethod
    def from_dict(data: dict) -> 'PersistData':
        return PersistData(
            season=SeasonPersist.from_dict(data.get('season')),
            zones={key: ZonePersist.from_dict(value) for key, value in (data.get('zones') or {}).items()},
            actuators_off=dict(data.get('actuators_off') or {}),
            known_actuators=list(data.get('known_actuators') or []),
        )

    def to_dict(self) -> dict:
        return {'version': PERSIST_VERSION,
                'season': self.season.to_dict(),
                'zones': {key: value.to_dict() for key, value in self.zones.items()},
                'actuators_off': self.actuators_off,
                'known_actuators': self.known_actuators}
