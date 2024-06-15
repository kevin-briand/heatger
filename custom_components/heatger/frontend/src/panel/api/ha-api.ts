import { type HomeAssistant } from 'custom-card-helpers'
import type { Prog } from './prog/dto/prog'

interface ApiResponse {
  success: boolean
}

export const heatgerAddProg = async (hass: HomeAssistant, zoneId: string, prog: Prog[]): Promise<ApiResponse> => {
  return await hass.callApi<ApiResponse>('POST', 'heatger/prog/add', { zone_id: zoneId, prog })
}

export const heatgerRemoveProg = async (hass: HomeAssistant, zoneId: string, prog: Prog): Promise<ApiResponse> => {
  return await hass.callApi<ApiResponse>('POST', 'heatger/prog/remove', { zone_id: zoneId, prog })
}

export const heatgerRemoveAllProg = async (hass: HomeAssistant, zoneId: string): Promise<ApiResponse> => {
  return await hass.callApi<ApiResponse>('POST', 'heatger/prog/removeall', { zone_id: zoneId })
}

export const heatgerAddUser = async (hass: HomeAssistant, user: string): Promise<ApiResponse> => {
  return await hass.callApi<ApiResponse>('POST', 'heatger/user/add', { user })
}

export const heatgerRemoveUser = async (hass: HomeAssistant, user: string): Promise<ApiResponse> => {
  return await hass.callApi<ApiResponse>('POST', 'heatger/user/remove', { user })
}

export const heatgerAddZone = async (hass: HomeAssistant, name: string): Promise<ApiResponse> => {
  return await hass.callApi<ApiResponse>('POST', 'heatger/zone/add', { zone: name })
}

export const heatgerRemoveZone = async (hass: HomeAssistant, name: string): Promise<ApiResponse> => {
  return await hass.callApi<ApiResponse>('POST', 'heatger/zone/remove', { zone: name })
}
