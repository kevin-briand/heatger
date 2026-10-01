# Heatger for Home Assistant

Heatger is a heating and cooling manager for Home Assistant. It runs weekly programs per zone, follows the season
(heating, cooling or stop), waits for someone to be home before switching to Comfort, and drives two kinds of devices:

- the **pilot wire outputs** of a [heatger-server](https://github.com/kevin-briand/heatger-server) (electric radiators),
- any **thermostat** known by Home Assistant (`climate` entity): air conditioner, heat pump, connected radiator…

The integration comes with a configuration panel in the sidebar and a dashboard
[card](https://github.com/kevin-briand/heatger-card).

## Features

- Zones, each with its own devices, a **winter program** (heating season) and a **summer program** (cooling season)
- **Seasons**: Heating, Cooling or Stop, optionally until a date and then another season
- Pilot wire outputs and thermostats in the same zone, with Comfort / Eco setpoints per season
- Comfort only when someone is home (optional, based on `person` entities)
- Temporary override (Comfort / Eco until the next change or for a duration) and manual mode
- Changes made on a device outside of Heatger are respected until the next change of program
- Entities and services for your dashboards and automations
- English and French translations

## Installation

### With HACS

1. Go to **HACS**, open the menu (three dots, top right) > **Custom repositories**.
2. Add `https://github.com/kevin-briand/heatger` with the **Integration** category.
3. Find **Heatger** in the list and download it, then restart Home Assistant.
4. Go to **Settings > Devices & services > Add integration** and select **Heatger**.
5. Enter the IP address and the port of your heatger-server.

Pre-releases (beta versions) are only offered when the **Pre-release** switch of the Heatger update entity is on.

### Manual

1. Copy the `custom_components/heatger` folder into the `custom_components` folder of your Home Assistant configuration.
2. Restart Home Assistant, then add the integration as above (steps 4 and 5).

## Configuration: the Heatger panel

Everything is configured in the **Heatger** panel of the sidebar (administrators only), organised in tabs.

| Tab | What you do there |
| --- | --- |
| **Season** | Switch between Heating, Cooling and Stop; schedule a change ("Stop until 1 November, then Heating"). |
| **Zones** | Create, rename, order, enable or delete zones; choose the temperature sensor of a zone and its devices. |
| **Programs** | Edit the winter and summer programs of each zone on a weekly view; copy one program to the other. |
| **Setpoints** | Change the Comfort / Eco setpoints of every thermostat in one place, applied immediately. |
| **Presence** | Choose the persons to follow: Comfort is applied only if at least one of them is home. |

## How it works

### Seasons

| Season | Program used | Pilot wire outputs | Thermostats |
| --- | --- | --- | --- |
| **Heating** | winter | follow the zone (Comfort / Eco) | follow the zone if they have heating setpoints |
| **Cooling** | summer | frost-free | follow the zone if they have cooling setpoints |
| **Stop** | none | frost-free | turned off once, then left alone |

A season can end at a given date and be followed by another one (the frost-free of version 1 is now
"Stop until a date, then Heating").

### Zones and programs

A program is a list of changes ("Monday 07:00 → Comfort", "Monday 22:00 → Eco"). The zone keeps the state of the
last change until the next one.

- **Auto mode**: the zone follows the program. A temporary override (Comfort or Eco) lasts until the next change
  of the program, or for a given duration.
- **Manual mode**: the program is suspended, the state stays as set.
- **Presence**: when Comfort starts and nobody is home, the zone waits in Eco and switches to Comfort as soon as
  someone comes home.

### Devices

- **Pilot wire**: an output of the heatger-server (`zone1`, `zone2`…). Comfort, Eco or frost-free.
- **Thermostat**: a `climate` entity. For each season it supports (its `hvac_modes`), you choose whether Heatger
  drives it and its Comfort and Eco setpoints: a temperature, a preset of the device, or off.
  - Setpoints are checked against the limits of the device, and an Eco warmer than Comfort when heating (or colder
    when cooling) is refused.
  - **Out of season** (no setpoints for the current season, or season Stop), the device is turned off once when the
    season starts, then Heatger no longer touches it: you can turn it on yourself.
  - **Manual changes**: a change made on the device, from a dashboard or by an automation is kept until the next
    change of the program or of the season.
  - **Unavailable device**: the order is sent as soon as it is back.

## Entities

| Entity | Per | Description |
| --- | --- | --- |
| `climate.heatger_<zone>` | zone | Mode *auto* = program, *heat* / *cool* = manual; preset *comfort* / *eco* = state (override in auto mode). Current temperature from the zone sensor. Attributes: `next_change`, `override_until`, `waiting_presence`, `season`. |
| `sensor.heatger_<zone>_next_change` | zone | Date of the next change of the program. |
| `binary_sensor.heatger_<zone>_waiting_for_presence` | zone | On while Comfort waits for someone to come home. |
| `number.heatger_<zone>_<device>_comfort_heating`… | thermostat | Comfort / Eco temperature setpoints of each thermostat, per season (only for setpoints that are temperatures). |
| `select.heatger_season` | – | Current season. |
| `select.heatger_next_season` | – | Season that follows the programmed end. |
| `datetime.heatger_end_of_the_season` | – | End of the current season (empty = no end). |
| `sensor.heatger_electric_meter` | – | Electric meter of the heatger-server. |

Entity ids depend on the language of your installation (for example `select.heatger_saison` in French).

## Services

### `heatger.set_season`

```yaml
action: heatger.set_season
data:
  season: stop               # heating | cooling | stop
  until: "2026-11-01 00:00:00"  # optional
  next: heating              # optional, season after `until`
```

### `heatger.set_zone_state`

```yaml
action: heatger.set_zone_state
data:
  zone: Jour        # name, id or number of the zone
  state: comfort    # comfort | eco | program (back to the program)
  duration: "02:00:00"  # optional, otherwise until the next change of the program
```

### `heatger.toggle`

Kept from version 1: toggles the state (Comfort / Eco until the next change) or the mode (Auto / Manual) of the
zone number N.

```yaml
action: heatger.toggle
data:
  zone: 1
  type: state   # state | mode
```

## Migration from version 1

The data is migrated automatically at the first start of version 2:

- each zone keeps its program as the winter program (also copied to the summer program) and gets a pilot wire
  device on its server output;
- a running frost-free becomes the season *Stop* until its end date, then *Heating*.

A copy of the version 1 data is kept in `.storage/heatger-config-v1-backup` and `.storage/heatger-persist-v1-backup`.
To go back to version 1, restore these files as `heatger-config` and `heatger-persist` before installing it.

Update the [card](https://github.com/kevin-briand/heatger-card) to version 2 as well to see and switch the seasons.

## Dashboard card

The [Heatger card](https://github.com/kevin-briand/heatger-card) shows each zone with its state, mode and next
change, and lets you switch the season.

## Development

The panel is written in TypeScript with Lit, in `custom_components/heatger/frontend`:

```bash
cd custom_components/heatger/frontend
npm install
npm run build   # compiles to dist/heatger-panel.js, loaded by Home Assistant
```

Python tests: `pip install -r requirements.test.txt` then `pytest`.
