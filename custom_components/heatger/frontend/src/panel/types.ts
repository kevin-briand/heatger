export type ProgramKey = 'winter' | 'summer'
export type SeasonKey = 'heating' | 'cooling' | 'stop'
export type SetpointKey = 'heat' | 'cool'
export type StateKey = 'comfort' | 'eco'

// a setpoint is a temperature, "off", or a preset of the device
export type Setpoint = number | 'off' | { preset: string }

export interface Setpoints {
  comfort: Setpoint
  eco: Setpoint
}

export interface ScheduleItem {
  day: number
  hour: string
  state: number
}

export interface ActuatorConfig {
  id?: string
  type: 'pilot_wire' | 'climate'
  name: string
  output?: string
  entity_id?: string
  heat?: Setpoints | null
  cool?: Setpoints | null
}

export interface ActuatorInfo {
  id: string
  type: string
  name: string
  output?: string
  order?: string | null
  entity_id?: string
  manual?: boolean
  available?: boolean
  controlled?: boolean
}

export interface ZoneLive {
  id: string
  number: number
  name: string
  state: number
  mode: number
  nextSwitch: number
  nextChange: string | null
  isPing: boolean
  override: { state: number, until: string | null } | null
  actuators: ActuatorInfo[]
}

export interface ZoneConfig {
  id?: string
  name: string
  enabled: boolean
  programs: Record<ProgramKey, ScheduleItem[]>
  actuators: ActuatorConfig[]
  temperature_sensor: string | null
  live?: ZoneLive | null
}

export interface SeasonInfo {
  season: SeasonKey
  until: string | null
  next: SeasonKey
  remaining: number
}

export interface HeatgerConfig {
  zones: ZoneConfig[]
  users: string[]
  season: SeasonInfo
}

export interface ClimateEntityInfo {
  entity_id: string
  name: string
  available: boolean
  hvac_modes: string[]
  preset_modes: string[]
  min_temp: number | null
  max_temp: number | null
}

export interface SaveResult {
  success: boolean
  errors: string[]
  id?: string
}

export const SEASONS: SeasonKey[] = ['heating', 'cooling', 'stop']
export const PROGRAMS: ProgramKey[] = ['winter', 'summer']
