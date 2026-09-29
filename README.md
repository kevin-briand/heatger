# Heatger for Home Assistant
## Description
This integration is a heater manager, it provides a clock program and can track user presence to activate comfort mode.
This integration is a part of [heatger-server](https://github.com/kevin-briand/heatger-server).

features include :
- multiple zones
- clock program
- Wait until user is home to return to Comfort mode

## Installation

### With HACS
- Go to the HACS panel
- select 3 dots in the top right corner > Custom repositories
- paste https://github.com/kevin-briand/heatger and select integration category
- find the heatger integration in the list and download it
- go to Settings > Devices & services > add integration
- select Heatger
- fill out the form

### Manual
To install this integration, follow these steps.
- add the custom_components folder into the home assistant config folder
- go to Settings > Devices & services > add integration
- select Heatger
- fill out the form

## Use

### Concepts
- **Season** (global): *heating*, *cooling* or *stop*, optionally until a date then another season
  (the old frost-free is the season *stop* until a date).
- **Zones**: each zone has a winter program (heating season) and a summer program (cooling season),
  a mode auto / manual, and waits for someone at home before switching to comfort.
- **Actuators** of a zone, configured in the Heatger panel:
  - *pilot wire*: an output of the heatger server. Heating season: follows the zone; other seasons: frost-free.
  - *thermostat*: any `climate` entity (air conditioner, heat pump, connected radiator...), with comfort / eco
    setpoints per season (a temperature, a preset of the device, or off). Out of season the device is turned off
    once, then left alone. A change made outside of Heatger is respected until the next change of state.

### Entities
- per zone: a `climate` entity (hvac mode *auto* = program, *heat*/*cool* = manual, preset comfort / eco),
  the next change (`sensor`), waiting for presence (`binary_sensor`), the temperature setpoints (`number`)
- global: the season and the next season (`select`), the end of the season (`datetime`)

### Services
- `heatger.set_season`: season, optional end date and next season
- `heatger.set_zone_state`: zone (name, id or number), comfort / eco / program, optional duration
- `heatger.toggle`: toggle the state or the mode of the zone number N (version 1)

### Migration from the version 1
The data is migrated at the first start: each zone gets a pilot wire actuator on its output, the program becomes
the winter and the summer program, a running frost-free becomes the season *stop*.
A copy of the version 1 data is kept in `.storage/heatger-config-v1-backup` and `.storage/heatger-persist-v1-backup`.

## Frontend card
You can also add a [card](https://github.com/kevin-briand/heatger-card)
