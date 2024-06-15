import { type Prog } from '../../api/prog/dto/prog'

export interface ZoneInfo {
  name: string
  enabled: boolean
  prog: Prog[]
}
