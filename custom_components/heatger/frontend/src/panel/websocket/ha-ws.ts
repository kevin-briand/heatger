import { type HomeAssistant } from 'custom-card-helpers'
import { type ZoneInfo } from './dto/zone-info.dto'
import { type HassEntityBase } from 'home-assistant-js-websocket'

export const heatgerGetProg = async (hass: HomeAssistant, zoneId: string): Promise<ZoneInfo> => {
  return await hass.callWS<ZoneInfo>({ type: 'heatger_get_prog', zone_id: zoneId })
}

export const heatgerGetZones = async (hass: HomeAssistant): Promise<Record<string, ZoneInfo>> => {
  return await hass.callWS<Record<string, ZoneInfo>>({ type: 'heatger_get_zones' })
}

export const heatgerGetAvailablePersons = async (hass: HomeAssistant): Promise<HassEntityBase[]> => {
  return await hass.callWS<HassEntityBase[]>({ type: 'heatger_get_available_persons' })
}

export const heatgerGetSelectedPersons = async (hass: HomeAssistant): Promise<string[]> => {
  return await hass.callWS<string[]>({ type: 'heatger_get_selected_persons' })
}
