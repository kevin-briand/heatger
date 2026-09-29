import { html, nothing, type TemplateResult } from 'lit'
import type { ClimateEntityInfo, Setpoint, SetpointKey, StateKey } from './types'

/** input of a thermostat setpoint: a temperature, a preset of the device or off (zone editor + setpoints tab) */

export type SetpointKind = 'temperature' | 'preset' | 'off'

export const kindOf = (setpoint: Setpoint): SetpointKind => {
  if (setpoint === 'off') return 'off'
  if (typeof setpoint === 'object') return 'preset'
  return 'temperature'
}

const DEFAULT_TEMPERATURES: Record<SetpointKey, Record<StateKey, number>> = {
  heat: { comfort: 20, eco: 17 },
  cool: { comfort: 25, eco: 28 }
}

/** new value when the kind changes */
export const setpointOfKind = (kind: SetpointKind, key: SetpointKey, stateKey: StateKey,
  info: ClimateEntityInfo | undefined): Setpoint => {
  if (kind === 'off') return 'off'
  if (kind === 'preset') {
    const presets = info?.preset_modes ?? []
    return { preset: presets.includes(stateKey) ? stateKey : presets[0] ?? stateKey }
  }
  return DEFAULT_TEMPERATURES[key][stateKey]
}

export const renderSetpointInput = (t: (key: string) => string, key: SetpointKey, stateKey: StateKey,
  value: Setpoint, info: ClimateEntityInfo | undefined, onChange: (value: Setpoint) => void): TemplateResult<1> => {
  const kind = kindOf(value)
  const presets = info?.preset_modes ?? []
  let input: TemplateResult<1> | typeof nothing = nothing
  if (kind === 'temperature') {
    const temperature = value as number
    const min = info?.min_temp ?? 5
    const max = info?.max_temp ?? 35
    const step = (delta: number): void => { onChange(Math.min(max, Math.max(min, Math.round((temperature + delta) * 2) / 2))) }
    input = html`
      <span class="temperature">
        <button class="icon-btn small" title="-0,5 °C" @click="${() => { step(-0.5) }}"><ha-icon icon="mdi:minus"></ha-icon></button>
        <input type="number" step="0.5" min="${min}" max="${max}" .value="${String(temperature)}"
          @change="${(e: Event) => { const v = parseFloat((e.target as HTMLInputElement).value); if (!isNaN(v)) onChange(v) }}"/>
        <button class="icon-btn small" title="+0,5 °C" @click="${() => { step(0.5) }}"><ha-icon icon="mdi:plus"></ha-icon></button>
        <span class="unit">°C</span>
      </span>`
  } else if (kind === 'preset') {
    const current = (value as { preset: string }).preset
    input = html`<select class="preset" @change="${(e: Event) => { onChange({ preset: (e.target as HTMLSelectElement).value }) }}">
      ${[...new Set([current, ...presets])].map((preset) => html`<option value="${preset}" ?selected="${preset === current}">${preset}</option>`)}
    </select>`
  }
  return html`
    <div class="setpoint-input">
      <select class="kind" @change="${(e: Event) => { onChange(setpointOfKind((e.target as HTMLSelectElement).value as SetpointKind, key, stateKey, info)) }}">
        <option value="temperature" ?selected="${kind === 'temperature'}">${t('panel.zone.kindTemperature')}</option>
        ${presets.length > 0 || kind === 'preset'
          ? html`<option value="preset" ?selected="${kind === 'preset'}">${t('panel.zone.kindPreset')}</option>`
          : nothing}
        <option value="off" ?selected="${kind === 'off'}">${t('panel.zone.kindOff')}</option>
      </select>
      ${input}
    </div>`
}
