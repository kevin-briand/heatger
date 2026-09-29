"""Migration of the stored data from the version 1 (zones zone1, zone2... and frost-free) to the version 2"""
from __future__ import annotations

import copy
import datetime
import logging
from typing import Optional

from .const import ACTUATOR_PILOT_WIRE, PROGRAM_SUMMER, PROGRAM_WINTER
from .models import (ActuatorConfig, CONFIG_VERSION, HeatgerConfig, PersistData, Schedule,
                     SeasonPersist, ZoneConfig, ZonePersist, new_id, sort_schedules, str_to_datetime)
from .shared.enum.mode import Mode
from .shared.enum.season import Season
from .shared.enum.state import State

_LOGGER = logging.getLogger(__name__)
ZONE_PREFIX = 'zone'


def is_v1_config(data: Optional[dict]) -> bool:
    """version 1: the zones are a dict {"zone1": {...}}"""
    return bool(data) and data.get('version') != CONFIG_VERSION and isinstance(data.get('zones'), dict)


def _zone_number(key: str) -> int:
    suffix = key[len(ZONE_PREFIX):]
    return int(suffix) if key.startswith(ZONE_PREFIX) and suffix.isdigit() else 10_000


def _parse_program(raw: list) -> list[Schedule]:
    schedules = []
    for item in raw or []:
        try:
            schedule = Schedule.from_dict(item)
        except (KeyError, TypeError, ValueError):
            _LOGGER.warning('Migration: invalid schedule ignored: %s', item)
            continue
        if schedule.is_valid() and schedule not in schedules:
            schedules.append(schedule)
    return sort_schedules(schedules)


def migrate_v1(config_raw: dict, persist_raw: Optional[dict], now: datetime.datetime) \
        -> tuple[HeatgerConfig, PersistData]:
    """convert the version 1 data.

    - each zoneN gets a stable id and a pilot wire actuator on the server output zoneN
    - the program becomes the winter program, and is copied as the initial summer program
    - a running frost-free becomes the season "stop" until its end date, then "heating"
    """
    config = HeatgerConfig(users=list(config_raw.get('users') or []))
    ids: dict[str, str] = {}
    for key in sorted(config_raw['zones'], key=_zone_number):
        raw = config_raw['zones'][key] or {}
        program = _parse_program(raw.get('prog'))
        zone = ZoneConfig(
            id=new_id(),
            name=str(raw.get('name') or key),
            enabled=bool(raw.get('enabled', True)),
            programs={PROGRAM_WINTER: program, PROGRAM_SUMMER: copy.deepcopy(program)},
            actuators=[ActuatorConfig(id=new_id(), type=ACTUATOR_PILOT_WIRE, name='Fil pilote', output=key)],
        )
        ids[key] = zone.id
        config.zones.append(zone)

    persist = PersistData()
    persist_raw = persist_raw or {}
    for raw in persist_raw.get('zones') or []:
        zone_id = ids.get(raw.get('zone_id'))
        if zone_id is None:
            continue
        try:
            state = State(int(raw.get('state', State.ECO.value)))
            mode = Mode(int(raw.get('mode', Mode.AUTO.value)))
        except (TypeError, ValueError):
            continue
        persist.zones[zone_id] = ZonePersist(state=State.ECO if state == State.FROSTFREE else state, mode=mode)

    frost_free_end = str_to_datetime(persist_raw.get('frost_free'))
    if frost_free_end and frost_free_end > now:
        persist.season = SeasonPersist(Season.STOP, frost_free_end, Season.HEATING)
    else:
        persist.season = SeasonPersist(Season.HEATING)
    _LOGGER.info('Heatger data migrated to version 2 (%d zones)', len(config.zones))
    return config, persist


def load_data(config_raw: Optional[dict], persist_raw: Optional[dict], now: datetime.datetime) \
        -> tuple[HeatgerConfig, PersistData, bool]:
    """return (config, persisted states, migrated) from the raw stored data"""
    if is_v1_config(config_raw):
        config, persist = migrate_v1(config_raw, persist_raw, now)
        return config, persist, True
    config = HeatgerConfig.from_dict(config_raw or {})
    if persist_raw and persist_raw.get('version') == 2:
        persist = PersistData.from_dict(persist_raw)
    else:
        persist = PersistData()
    return config, persist, config_raw is None
