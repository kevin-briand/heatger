import { html, nothing, type TemplateResult } from 'lit'
import type { SeasonKey } from './types'

/** small render helpers shared by the cards of the panel */

export const SEASON_ICONS: Record<SeasonKey, string> = {
  heating: 'mdi:fire',
  cooling: 'mdi:snowflake',
  stop: 'mdi:power'
}

export const STATE_ICONS: Record<number, string> = {
  0: 'mdi:sun-thermometer',
  1: 'mdi:leaf'
}

export const errorAlert = (error: string | string[] | null): TemplateResult<1> | typeof nothing => {
  if (error === null || (Array.isArray(error) && error.length === 0)) return nothing
  return html`
    <div class="alert error">
      <ha-icon icon="mdi:alert-circle-outline"></ha-icon>
      ${Array.isArray(error)
        ? html`<ul>${error.map((e) => html`<li>${e}</li>`)}</ul>`
        : html`<div>${error}</div>`}
    </div>`
}

export const infoAlert = (info: string | null): TemplateResult<1> | typeof nothing => {
  if (info === null) return nothing
  return html`<div class="alert info"><ha-icon icon="mdi:information-outline"></ha-icon><div>${info}</div></div>`
}

export const cardHeader = (icon: string, title: string, extra: TemplateResult<1> | typeof nothing = nothing): TemplateResult<1> => html`
  <div class="card-header-row">
    <ha-icon icon="${icon}"></ha-icon>
    <h1>${title}</h1>
    ${extra}
  </div>`

export const iconButton = (icon: string, label: string, onClick: () => void,
  options: { disabled?: boolean, danger?: boolean } = {}): TemplateResult<1> => html`
  <button class="icon-btn ${options.danger === true ? 'danger' : ''}" title="${label}" aria-label="${label}"
    ?disabled="${options.disabled === true}" @click="${onClick}">
    <ha-icon icon="${icon}"></ha-icon>
  </button>`

export const toggleSwitch = (checked: boolean, onChange: (checked: boolean) => void): TemplateResult<1> => html`
  <span class="switch">
    <input type="checkbox" .checked="${checked}"
      @change="${(e: Event) => { onChange((e.target as HTMLInputElement).checked) }}"/>
    <span class="slider"></span>
  </span>`
