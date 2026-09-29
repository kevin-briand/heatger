"""Constants for the Heatger integration."""

DOMAIN = "heatger"
IP = "ip"
PORT = "port"

# keys of hass.data[DOMAIN]
DATA_ZONE_MANAGER = 'zone_manager'
DATA_SEASON = 'season'
DATA_STORAGE = 'storage'
DATA_WS = 'WS'
DATA_SERVER_CONFIG = 'server_config'
DATA_ENTRY = 'entry'

# program keys, one program per season with a program
PROGRAM_WINTER = 'winter'
PROGRAM_SUMMER = 'summer'
PROGRAMS = [PROGRAM_WINTER, PROGRAM_SUMMER]

# actuator types
ACTUATOR_PILOT_WIRE = 'pilot_wire'
ACTUATOR_CLIMATE = 'climate'
ACTUATOR_TYPES = [ACTUATOR_PILOT_WIRE, ACTUATOR_CLIMATE]

# setpoint keys of a climate actuator, one per season where it can be controlled
SETPOINTS_HEAT = 'heat'
SETPOINTS_COOL = 'cool'
SETPOINT_OFF = 'off'

SERVICE_TOGGLE = 'toggle'
SERVICE_SET_ZONE_STATE = 'set_zone_state'
SERVICE_SET_SEASON = 'set_season'
