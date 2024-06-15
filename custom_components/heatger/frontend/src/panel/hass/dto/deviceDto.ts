export interface DeviceDto {
  id: string
  config_entries: string[]
  connections: Array<[string, string]>
  identifiers: Array<[string, string | number]>
  manufacturer: string
  model: string
  name: string
  sw_version: string
  via_device_id: string | null
  area_id: string | null
  name_by_user: string | null
  entry_type: string | null
  is_disabled: boolean
  device_class: string | null
  capabilities: object
  supported_features: number
}
