import { type HomeAssistant } from 'custom-card-helpers'
import { type HassEntityBase } from 'home-assistant-js-websocket'
import type { ClimateEntityInfo, HeatgerConfig, SaveResult, SeasonInfo, SetpointKey, Setpoints, ZoneConfig } from '../types'

export const heatgerGetConfig = async (hass: HomeAssistant): Promise<HeatgerConfig> => {
  return await hass.callWS<HeatgerConfig>({ type: 'heatger/config' })
}

export const heatgerGetClimateEntities = async (hass: HomeAssistant): Promise<ClimateEntityInfo[]> => {
  return await hass.callWS<ClimateEntityInfo[]>({ type: 'heatger/climate_entities' })
}

export const heatgerGetSeason = async (hass: HomeAssistant): Promise<SeasonInfo> => {
  return await hass.callWS<SeasonInfo>({ type: 'heatger/season' })
}

export const heatgerSaveZone = async (hass: HomeAssistant, zone: ZoneConfig): Promise<SaveResult> => {
  const payload = {
    id: zone.id,
    name: zone.name,
    enabled: zone.enabled,
    actuators: zone.actuators,
    temperature_sensor: zone.temperature_sensor
  }
  return await hass.callWS<SaveResult>({ type: 'heatger/zone/save', zone: payload })
}

export const heatgerDeleteZone = async (hass: HomeAssistant, zoneId: string): Promise<{ success: boolean }> => {
  return await hass.callWS<{ success: boolean }>({ type: 'heatger/zone/delete', zone_id: zoneId })
}

export const heatgerMoveZone = async (hass: HomeAssistant, zoneId: string, offset: number): Promise<{ success: boolean }> => {
  return await hass.callWS<{ success: boolean }>({ type: 'heatger/zone/move', zone_id: zoneId, offset })
}

export const heatgerGetAvailablePersons = async (hass: HomeAssistant): Promise<HassEntityBase[]> => {
  return await hass.callWS<HassEntityBase[]>({ type: 'heatger_get_available_persons' })
}

export const heatgerGetSelectedPersons = async (hass: HomeAssistant): Promise<string[]> => {
  return await hass.callWS<string[]>({ type: 'heatger_get_selected_persons' })
}

/** comfort / eco setpoints of a thermostat for a season, applied at once (reload = heatger reloads itself) */
export const heatgerSaveSetpoints = async (hass: HomeAssistant, actuatorId: string, key: SetpointKey,
  setpoints: Setpoints): Promise<SaveResult & { reload?: boolean }> => {
  return await hass.callWS<SaveResult & { reload?: boolean }>({ type: 'heatger/setpoints/save', actuator_id: actuatorId, key, setpoints })
}
