import { css, type CSSResultGroup, html, LitElement, nothing, type PropertyDeclaration, type TemplateResult } from 'lit'
import { type HomeAssistant, type Panel } from 'custom-card-helpers'
import { customElement, property, state } from 'lit/decorators.js'
import { localize } from '../../localize/localize'
import { style } from '../../style'
import { heatgerGetClimateEntities, heatgerGetConfig, heatgerSaveSetpoints } from '../websocket/ha-ws'
import type { ActuatorConfig, ClimateEntityInfo, SeasonKey, SetpointKey, Setpoints, StateKey, ZoneConfig } from '../types'
import { errorAlert, infoAlert, STATE_ICONS } from '../ui'
import { renderSetpointInput } from '../setpoint_input'

const SETPOINT_KEYS: SetpointKey[] = ['heat', 'cool']
const STATE_KEYS: StateKey[] = ['comfort', 'eco']
const SEASON_OF: Record<SetpointKey, SeasonKey> = { heat: 'heating', cool: 'cooling' }
const SEASON_ICON: Record<SetpointKey, string> = { heat: 'mdi:fire', cool: 'mdi:snowflake' }
const HVAC_MODE: Record<SetpointKey, string> = { heat: 'heat', cool: 'cool' }
const RELOAD_DELAY = 2500

const rowId = (actuator: ActuatorConfig, key: SetpointKey): string => `${actuator.id ?? ''}:${key}`

/**
 * Every setpoint of the thermostats in one place: changed and applied at once, without opening the zone editor.
 * Enabling a season for a device stays in the zone editor (it creates entities).
 */
@customElement('heatger-setpoints-card')
export class HeatgerSetpointsCard extends LitElement {
  @property({ attribute: false }) public hass!: HomeAssistant
  @property({ attribute: false }) public panel!: Panel
  @property({ type: Boolean, reflect: true }) public narrow!: boolean
  @property({ attribute: false }) public reload!: () => void
  @state() private zones: ZoneConfig[] = []
  @state() private climates: ClimateEntityInfo[] = []
  @state() private season: SeasonKey = 'heating'
  @state() private error: string | null = null
  @state() private info: string | null = null
  // rows being edited: actuator:key -> draft setpoints
  @state() private drafts: Record<string, Setpoints> = {}
  @state() private rowErrors: Record<string, string[]> = {}
  @state() private saving: string | null = null

  firstUpdated (): void {
    this.updateData()
  }

  requestUpdate (name?: PropertyKey, oldValue?: unknown, options?: PropertyDeclaration): void {
    super.requestUpdate(name, oldValue, options)
    if (name === 'panel') this.updateData()
  }

  private t (key: string): string {
    return localize(key, this.hass.language)
  }

  updateData (): void {
    Promise.all([heatgerGetConfig(this.hass), heatgerGetClimateEntities(this.hass)]).then(([config, climates]) => {
      this.zones = config.zones
      this.climates = climates
      this.season = config.season.season
      this.error = null
    }).catch((e: Error) => { this.error = e.message })
  }

  private climateInfo (entityId: string | undefined): ClimateEntityInfo | undefined {
    return this.climates.find((climate) => climate.entity_id === entityId)
  }

  private supports (actuator: ActuatorConfig, key: SetpointKey): boolean {
    const info = this.climateInfo(actuator.entity_id)
    return info === undefined || !info.available || info.hvac_modes.includes(HVAC_MODE[key])
  }

  // ---- edition

  private edit (actuator: ActuatorConfig, key: SetpointKey, stateKey: StateKey, value: Setpoints[StateKey]): void {
    const id = rowId(actuator, key)
    const current = this.drafts[id] ?? { ...(actuator[key] as Setpoints) }
    this.drafts = { ...this.drafts, [id]: { ...current, [stateKey]: value } }
    this.rowErrors = { ...this.rowErrors, [id]: [] }
  }

  private cancel (id: string): void {
    const { [id]: _, ...drafts } = this.drafts
    this.drafts = drafts
    this.rowErrors = { ...this.rowErrors, [id]: [] }
  }

  private async save (actuator: ActuatorConfig, key: SetpointKey): Promise<void> {
    const id = rowId(actuator, key)
    const draft = this.drafts[id]
    if (draft === undefined || actuator.id === undefined) return
    this.saving = id
    try {
      const result = await heatgerSaveSetpoints(this.hass, actuator.id, key, draft)
      if (!result.success) {
        this.rowErrors = { ...this.rowErrors, [id]: result.errors }
      } else {
        actuator[key] = draft
        this.cancel(id)
        if (result.reload === true) {
          this.info = this.t('panel.zone.reloading')
          setTimeout(() => { this.info = null; this.reload(); this.updateData() }, RELOAD_DELAY)
        } else {
          this.updateData()
        }
      }
    } catch (e) {
      this.rowErrors = { ...this.rowErrors, [id]: [(e as Error).message] }
    }
    this.saving = null
  }

  // ---- render

  private deviceStatus (actuator: ActuatorConfig): TemplateResult<1> | typeof nothing {
    const entity = actuator.entity_id !== undefined ? this.hass.states[actuator.entity_id] : undefined
    if (entity === undefined) return nothing
    if (entity.state === 'unavailable' || entity.state === 'unknown') {
      return html`<span class="badge">${this.t('panel.setpoints.unavailable')}</span>`
    }
    const current = entity.attributes.current_temperature as number | undefined
    const target = entity.attributes.temperature as number | undefined
    const preset = entity.attributes.preset_mode as string | undefined
    const parts = [
      this.t(`panel.setpoints.hvac.${entity.state}`) ?? entity.state,
      current !== undefined && current !== null ? `${current} °C` : null,
      target !== undefined && target !== null ? `→ ${target} °C` : (preset !== undefined && preset !== null ? `→ ${preset}` : null)
    ].filter((part) => part !== null)
    return html`<span class="badge ${entity.state === 'off' ? '' : 'on'}">${parts.join(' · ')}</span>`
  }

  private renderRow (actuator: ActuatorConfig, key: SetpointKey): TemplateResult<1> | typeof nothing {
    const saved = actuator[key]
    const current = this.season === SEASON_OF[key]
    if (saved == null) {
      if (!this.supports(actuator, key)) return nothing
      return html`
        <div class="row off">
          <div class="season-label"><ha-icon icon="${SEASON_ICON[key]}"></ha-icon>${this.t(`season.${SEASON_OF[key]}`)}</div>
          <div class="muted">${this.t('panel.setpoints.notControlled')}</div>
        </div>`
    }
    const id = rowId(actuator, key)
    const draft = this.drafts[id]
    const setpoints = draft ?? saved
    const info = this.climateInfo(actuator.entity_id)
    return html`
      <div class="row ${current ? 'current' : ''} ${draft !== undefined ? 'dirty' : ''}">
        <div class="season-label">
          <ha-icon icon="${SEASON_ICON[key]}"></ha-icon>${this.t(`season.${SEASON_OF[key]}`)}
          ${current ? html`<span class="badge now">${this.t('panel.setpoints.now')}</span>` : nothing}
        </div>
        <div class="values">
          ${STATE_KEYS.map((stateKey) => html`
            <div class="value">
              <span class="state ${stateKey}"><ha-icon icon="${STATE_ICONS[stateKey === 'comfort' ? 0 : 1]}"></ha-icon>${this.t(`state.${stateKey}`)}</span>
              ${renderSetpointInput(this.t.bind(this), key, stateKey, setpoints[stateKey], info,
                (value) => { this.edit(actuator, key, stateKey, value) })}
            </div>`)}
        </div>
        ${draft !== undefined
          ? html`
            <div class="row-actions">
              <button class="btn text" ?disabled="${this.saving === id}" @click="${() => { this.cancel(id) }}">${this.t('panel.cancel')}</button>
              <button class="btn" ?disabled="${this.saving === id}" @click="${() => { void this.save(actuator, key) }}">
                <ha-icon icon="mdi:check"></ha-icon>${this.t('panel.setpoints.apply')}</button>
            </div>`
          : nothing}
        ${errorAlert(this.rowErrors[id] !== undefined && this.rowErrors[id].length > 0 ? this.rowErrors[id] : null)}
      </div>`
  }

  private renderActuator (actuator: ActuatorConfig): TemplateResult<1> {
    return html`
      <div class="device">
        <div class="device-header">
          <ha-icon icon="mdi:thermostat"></ha-icon>
          <div class="main">
            <div class="title">${actuator.name !== '' ? actuator.name : actuator.entity_id}</div>
            <div class="subtitle">${actuator.entity_id}</div>
          </div>
          ${this.deviceStatus(actuator)}
        </div>
        ${SETPOINT_KEYS.map((key) => this.renderRow(actuator, key))}
      </div>`
  }

  private renderZone (zone: ZoneConfig): TemplateResult<1> | typeof nothing {
    const thermostats = zone.actuators.filter((actuator) => actuator.type === 'climate')
    if (thermostats.length === 0) return nothing
    const live = zone.live
    return html`
      <section>
        <h3 class="zone-title">
          <span>${zone.name}</span>
          ${live != null && this.season !== 'stop'
            ? html`<span class="badge ${live.state === 0 ? 'comfort' : 'eco'}">
                <ha-icon icon="${STATE_ICONS[live.state] ?? 'mdi:leaf'}"></ha-icon>${this.t(`state.${live.state === 0 ? 'comfort' : 'eco'}`)}</span>`
            : nothing}
          ${zone.enabled ? nothing : html`<span class="badge">${this.t('panel.zone.disabled')}</span>`}
        </h3>
        ${thermostats.map((actuator) => this.renderActuator(actuator))}
      </section>`
  }

  render (): TemplateResult<1> {
    const any = this.zones.some((zone) => zone.actuators.some((actuator) => actuator.type === 'climate'))
    return html`
      <ha-card>
        <div class="card-content">
          ${errorAlert(this.error)}
          ${infoAlert(this.info)}
          <p class="hint">${this.t('panel.setpoints.hint')}</p>
          ${any
            ? this.zones.map((zone) => this.renderZone(zone))
            : html`<div class="list-empty">${this.t('panel.setpoints.empty')}</div>`}
        </div>
      </ha-card>
    `
  }

  static get styles (): CSSResultGroup {
    return css`
      ${style}
      section + section {
        margin-top: 24px;
      }

      .zone-title {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 1.05rem;
        font-weight: 500;
        margin: 0 0 8px 0;
      }

      .device {
        border: 1px solid var(--hg-border);
        border-radius: var(--hg-radius);
        margin-bottom: 12px;
        overflow: hidden;
      }

      .device-header {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 10px 12px;
        flex-wrap: wrap;
      }

      .device-header > ha-icon {
        color: var(--state-icon-color, var(--primary-color));
      }

      .device-header .main {
        flex: 1;
        min-width: 140px;
      }

      .device-header .subtitle {
        color: var(--hg-muted);
        font-size: 0.8rem;
      }

      .badge.on {
        background-color: color-mix(in srgb, var(--hg-comfort) 18%, transparent);
        color: var(--primary-text-color);
      }

      .badge.now {
        background-color: rgba(var(--rgb-primary-color, 3, 169, 244), 0.18);
        color: var(--primary-color);
      }

      .row {
        display: grid;
        grid-template-columns: 170px 1fr;
        gap: 8px 12px;
        align-items: center;
        padding: 10px 12px;
        border-top: 1px solid var(--hg-border);
      }

      .row.current {
        background-color: var(--hg-field-bg);
      }

      .row.dirty {
        box-shadow: inset 3px 0 0 var(--primary-color);
      }

      .season-label {
        display: flex;
        align-items: center;
        gap: 6px;
        flex-wrap: wrap;
        font-size: 0.9rem;
        --mdc-icon-size: 18px;
      }

      .season-label > ha-icon {
        color: var(--hg-muted);
      }

      .row.current .season-label > ha-icon {
        color: var(--primary-color);
      }

      .values {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }

      .value {
        display: grid;
        grid-template-columns: 90px 1fr;
        align-items: center;
        gap: 8px;
      }

      .state {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        font-size: 0.85rem;
        --mdc-icon-size: 16px;
      }

      .state.comfort ha-icon {
        color: var(--hg-comfort);
      }

      .state.eco ha-icon {
        color: var(--hg-eco);
      }

      .row-actions {
        grid-column: 1 / -1;
        display: flex;
        justify-content: flex-end;
        gap: 8px;
      }

      .row .alert {
        grid-column: 1 / -1;
        margin: 0;
      }

      .row.off .muted {
        color: var(--hg-muted);
        font-size: 0.85rem;
      }

      @media (max-width: 600px) {
        .row {
          grid-template-columns: 1fr;
        }
      }
    `
  }
}
