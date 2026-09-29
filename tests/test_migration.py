"""Test the migration of the version 1 data (zone1, zone2... and frost-free)."""
import datetime
from zoneinfo import ZoneInfo

from custom_components.heatger.migration import load_data
from custom_components.heatger.shared.enum.mode import Mode
from custom_components.heatger.shared.enum.season import Season
from custom_components.heatger.shared.enum.state import State

PARIS = ZoneInfo('Europe/Paris')
NOW = datetime.datetime(2026, 9, 29, 12, 0, tzinfo=PARIS)
PROG = [{'day': 0, 'hour': '07:00:00', 'state': 0}, {'day': 0, 'hour': '22:00:00', 'state': 1}]
V1_CONFIG = {'zones': {'zone2': {'name': 'Nuit', 'enabled': True, 'prog': PROG},
                       'zone1': {'name': 'Jour', 'enabled': True, 'prog': PROG}},
             'users': ['person.kevin'], 'ws_url': 'http://1.2.3.4:5000'}


def test_migration_zones_and_programs():
    config, persist, migrated = load_data(V1_CONFIG, None, NOW)
    assert migrated
    assert [zone.name for zone in config.zones] == ['Jour', 'Nuit']
    assert [zone.actuators[0].output for zone in config.zones] == ['zone1', 'zone2']
    assert config.zones[0].programs['winter'] == config.zones[0].programs['summer']
    assert len(config.zones[0].programs['winter']) == 2
    assert config.users == ['person.kevin']
    assert persist.season.current == Season.HEATING


def test_migration_frost_free_becomes_season_stop():
    persist_v1 = {'zones': [{'zone_id': 'zone1', 'state': 0, 'mode': 1}], 'frost_free': '2026-11-01 00:00'}
    config, persist, _ = load_data(V1_CONFIG, persist_v1, NOW)
    assert persist.season.current == Season.STOP
    # the stored date is a local date (time zone of Home Assistant)
    assert persist.season.until.replace(tzinfo=None) == datetime.datetime(2026, 11, 1)
    assert persist.season.next == Season.HEATING
    jour = persist.zones[config.zones[0].id]
    assert jour.mode == Mode.MANUAL and jour.state == State.COMFORT


def test_v2_data_is_kept():
    config, persist, _ = load_data(V1_CONFIG, None, NOW)
    config2, persist2, migrated = load_data(config.to_dict(), persist.to_dict(), NOW)
    assert not migrated
    assert [zone.id for zone in config2.zones] == [zone.id for zone in config.zones]
    assert persist2.season == persist.season
