import { type HomeAssistant } from 'custom-card-helpers'
import type { ProgramKey, ScheduleItem } from '../types'

interface ApiResponse {
  success: boolean
  id?: string
}

export const heatgerAddProg = async (hass: HomeAssistant, zoneId: string, program: ProgramKey, prog: ScheduleItem[]): Promise<ApiResponse> => {
  return await hass.callApi<ApiResponse>('POST', 'heatger/prog/add', { zone_id: zoneId, program, prog })
}

export const heatgerRemoveProg = async (hass: HomeAssistant, zoneId: string, program: ProgramKey, prog: ScheduleItem): Promise<ApiResponse> => {
  return await hass.callApi<ApiResponse>('POST', 'heatger/prog/remove', { zone_id: zoneId, program, prog })
}

export const heatgerRemoveAllProg = async (hass: HomeAssistant, zoneId: string, program: ProgramKey): Promise<ApiResponse> => {
  return await hass.callApi<ApiResponse>('POST', 'heatger/prog/removeall', { zone_id: zoneId, program })
}

export const heatgerCopyProg = async (hass: HomeAssistant, zoneId: string, from: ProgramKey, to: ProgramKey): Promise<ApiResponse> => {
  return await hass.callApi<ApiResponse>('POST', 'heatger/prog/copy', { zone_id: zoneId, from, to })
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
