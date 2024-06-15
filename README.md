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
- select Massa Node
- fill out the form

## Use

### States
The integration provides the current state of zones as entities, so you can use them for your automations.

### Service
The integration provides a service to toggle state or mode of zones.

To use it, you should provide params in the payload :
 - type: the type of toggle (state or mode)
 - zone: the zone you want to update (number)

## Frontend card
You can also add a [card](https://github.com/kevin-briand/HA-massa-node-card)
