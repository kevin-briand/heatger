import { css, type CSSResultGroup, html, LitElement, nothing, type PropertyValues, type TemplateResult } from 'lit'
import { type HomeAssistant } from 'custom-card-helpers'
import { customElement, property, state } from 'lit/decorators.js'
import { localize } from '../../localize/localize'
import { style } from '../../style'
import { heatgerSaveZone } from '../websocket/ha-ws'
import { errorAlert, iconButton, toggleSwitch } from '../ui'
import { renderSetpointInput } from '../setpoint_input'
import type {
  ActuatorConfig, ClimateEntityInfo, SetpointKey, Setpoints, StateKey, ZoneConfig
} from '../types'

const SETPOINT_KEYS: SetpointKey[] = ['heat', 'cool']
const STATE_KEYS: StateKey[] = ['comfort', 'eco']
const DEFAULT_SETPOINTS: Record<SetpointKey, Setpoints> = {
  heat: { comfort: 20, eco: 17 },
  cool: { comfort: 25, eco: 'off' }
}
// hvac mode needed on the device for each setpoints
const HVAC_MODE: Record<SetpointKey, string> = { heat: 'heat', cool: 'cool' }

const clone = <T>(value: T): T => JSON.parse(JSON.stringify(value)) as T

/**
 * Edit a zone: name, enabled, temperature sensor, actuators (pilot wire outputs, thermostats and their setpoints).
 * The programs are edited in the program card.
 */
@customElement('heatger-zone-editor')
export class HeatgerZoneEditor extends LitElement {
  @property({ attribute: false }) public hass!: HomeAssistant
  @property({ attribute: false }) public zone!: ZoneConfig
  @property({ attribute: false }) public climates: ClimateEntityInfo[] = []
  @property({ attribute: false }) public done!: (saved: boolean) => void
  @state() private draft!: ZoneConfig
  @state() private errors: string[] = []
  @state() private saving = false

  protected willUpdate (changed: PropertyValues): void {
    // a new draft only for another zone: the data of the panel can be read again while editing
    const previous = changed.get('zone') as ZoneConfig | undefined
    if (changed.has('zone') && (this.draft === undefined || previous === undefined || previous.id !== this.zone.id)) {
      this.draft = clone(this.zone)
      this.errors = []
    }
  }

  private t (key: string): string {
    return localize(key, this.hass.language)
  }

  private changed (): void {
    this.errors = []
    this.draft = { ...this.draft }
  }

  private climateInfo (entityId: string | undefined): ClimateEntityInfo | undefined {
    return this.climates.find((climate) => climate.entity_id === entityId)
  }

  /** seasons the device can do (unknown device: both) */
  private supports (actuator: ActuatorConfig, key: SetpointKey): boolean {
    const info = this.climateInfo(actuator.entity_id)
    if (info === undefined || !info.available) return true
    return info.hvac_modes.includes(HVAC_MODE[key])
  }

  private temperatureSensors (): Array<{ id: string, name: string }> {
    return Object.values(this.hass.states)
      .filter((entity) => entity.entity_id.startsWith('sensor.') && entity.attributes.device_class === 'temperature')
      .map((entity) => ({ id: entity.entity_id, name: String(entity.attributes.friendly_name ?? entity.entity_id) }))
      .sort((a, b) => a.name.localeCompare(b.name))
  }

  // ---- actions

  private addActuator (type: 'pilot_wire' | 'climate'): void {
    const actuator: ActuatorConfig = type === 'pilot_wire'
      ? { type, name: this.t('panel.zone.pilotWire'), output: '' }
      : { type, name: '', entity_id: '', heat: null, cool: null }
    this.draft.actuators = [...this.draft.actuators, actuator]
    this.changed()
  }

  private removeActuator (index: number): void {
    this.draft.actuators = this.draft.actuators.filter((_, i) => i !== index)
    this.changed()
  }

  private setClimateEntity (actuator: ActuatorConfig, entityId: string): void {
    actuator.entity_id = entityId
    const info = this.climateInfo(entityId)
    if (actuator.name === '' && info !== undefined) actuator.name = info.name
    // setpoints only for the seasons the device supports, heating by default
    if (actuator.heat == null && actuator.cool == null) {
      if (this.supports(actuator, 'heat')) actuator.heat = clone(DEFAULT_SETPOINTS.heat)
      else if (this.supports(actuator, 'cool')) actuator.cool = clone(DEFAULT_SETPOINTS.cool)
    }
    this.changed()
  }

  private toggleSeason (actuator: ActuatorConfig, key: SetpointKey, enabled: boolean): void {
    actuator[key] = enabled ? clone(DEFAULT_SETPOINTS[key]) : null
    this.changed()
  }

  private async save (): Promise<void> {
    this.saving = true
    this.errors = []
    try {
      const result = await heatgerSaveZone(this.hass, this.draft)
      if (result.success) {
        this.done(true)
      } else {
        this.errors = result.errors
      }
    } catch (e) {
      this.errors = [(e as Error).message]
    }
    this.saving = false
  }

  // ---- render

  private renderSetpoint (actuator: ActuatorConfig, key: SetpointKey, setpoints: Setpoints, stateKey: StateKey): TemplateResult<1> {
    return html`
      <div class="setpoint">
        <span class="badge ${stateKey}"><ha-icon icon="${stateKey === 'comfort' ? 'mdi:sun-thermometer' : 'mdi:leaf'}"></ha-icon>${this.t(`state.${stateKey}`)}</span>
        ${renderSetpointInput(this.t.bind(this), key, stateKey, setpoints[stateKey], this.climateInfo(actuator.entity_id),
          (value) => { setpoints[stateKey] = value; this.changed() })}
      </div>
    `
  }

  private renderSeason (actuator: ActuatorConfig, key: SetpointKey): TemplateResult<1> | typeof nothing {
    const setpoints = actuator[key]
    if (!this.supports(actuator, key) && setpoints == null) return nothing
    return html`
      <div class="season ${setpoints != null ? 'on' : ''}">
        <label class="switch-row">
          <span class="season-title">
            <ha-icon icon="${key === 'heat' ? 'mdi:fire' : 'mdi:snowflake'}"></ha-icon>
            ${this.t(`panel.zone.controlled_${key}`)}
          </span>
          ${toggleSwitch(setpoints != null, (checked) => { this.toggleSeason(actuator, key, checked) })}
        </label>
        ${setpoints != null
          ? STATE_KEYS.map((stateKey) => this.renderSetpoint(actuator, key, setpoints, stateKey))
          : html`<p class="hint small">${this.t('panel.zone.notControlled')}</p>`}
      </div>
    `
  }

  private renderActuatorHeader (icon: string, title: string, subtitle: string, index: number): TemplateResult<1> {
    return html`
      <div class="actuator-header">
        <ha-icon icon="${icon}"></ha-icon>
        <div class="main">
          <div class="title">${title}</div>
          ${subtitle !== '' ? html`<div class="subtitle">${subtitle}</div>` : nothing}
        </div>
        ${iconButton('mdi:delete-outline', this.t('panel.delete'), () => { this.removeActuator(index) }, { danger: true })}
      </div>`
  }

  private renderActuator (actuator: ActuatorConfig, index: number): TemplateResult<1> {
    if (actuator.type === 'pilot_wire') {
      return html`
        <div class="actuator">
          ${this.renderActuatorHeader('mdi:radiator', this.t('panel.zone.pilotWire'), this.t('panel.zone.pilotWireHint'), index)}
          <div class="field">
            <label>${this.t('panel.zone.output')}</label>
            <div class="value">
              <input type="text" placeholder="zone1" .value="${actuator.output ?? ''}"
                @change="${(e: Event) => { actuator.output = (e.target as HTMLInputElement).value.trim(); this.changed() }}"/>
            </div>
          </div>
        </div>
      `
    }
    const info = this.climateInfo(actuator.entity_id)
    const selected = actuator.entity_id !== '' && actuator.entity_id !== undefined
    return html`
      <div class="actuator">
        ${this.renderActuatorHeader('mdi:thermostat', actuator.name !== '' ? actuator.name : this.t('panel.zone.thermostat'),
          selected ? actuator.entity_id ?? '' : this.t('panel.zone.thermostatHint'), index)}
        <div class="field">
          <label>${this.t('panel.zone.entity')}</label>
          <div class="value">
            <select @change="${(e: Event) => { this.setClimateEntity(actuator, (e.target as HTMLSelectElement).value) }}">
              <option value="" ?selected="${!selected}">${this.t('panel.zone.chooseEntity')}</option>
              ${this.climates.map((climate) => html`
                <option value="${climate.entity_id}" ?selected="${climate.entity_id === actuator.entity_id}">
                  ${climate.name}</option>`)}
            </select>
          </div>
        </div>
        <div class="field">
          <label>${this.t('panel.general.name')}</label>
          <div class="value">
            <input type="text" .value="${actuator.name}"
              @change="${(e: Event) => { actuator.name = (e.target as HTMLInputElement).value; this.changed() }}"/>
          </div>
        </div>
        ${info !== undefined && !info.available
          ? html`<div class="alert info"><ha-icon icon="mdi:lan-disconnect"></ha-icon><div>${this.t('panel.zone.unavailable')}</div></div>`
          : nothing}
        ${selected ? SETPOINT_KEYS.map((key) => this.renderSeason(actuator, key)) : nothing}
      </div>
    `
  }

  render (): TemplateResult<1> {
    if (this.draft === undefined) return html``
    return html`
      <div class="editor">
        <h3 class="section">${this.t('panel.zone.general')}</h3>
        <div class="field">
          <label>${this.t('panel.general.name')}</label>
          <div class="value">
            <input type="text" .value="${this.draft.name}"
              @change="${(e: Event) => { this.draft.name = (e.target as HTMLInputElement).value; this.changed() }}"/>
          </div>
        </div>
        <div class="field">
          <label>${this.t('panel.zone.temperatureSensor')}</label>
          <div class="value">
            <select @change="${(e: Event) => { const v = (e.target as HTMLSelectElement).value; this.draft.temperature_sensor = v === '' ? null : v; this.changed() }}">
              <option value="" ?selected="${this.draft.temperature_sensor === null}">${this.t('panel.zone.none')}</option>
              ${this.temperatureSensors().map((sensor) => html`
                <option value="${sensor.id}" ?selected="${sensor.id === this.draft.temperature_sensor}">${sensor.name}</option>`)}
            </select>
          </div>
        </div>
        <label class="switch-row">
          <span>${this.t('panel.zone.enabled')}</span>
          ${toggleSwitch(this.draft.enabled, (checked) => { this.draft.enabled = checked; this.changed() })}
        </label>

        <h3 class="section">${this.t('panel.zone.actuators')}</h3>
        ${this.draft.actuators.length === 0 ? html`<p class="hint">${this.t('panel.zone.noActuatorHint')}</p>` : nothing}
        ${this.draft.actuators.map((actuator, index) => this.renderActuator(actuator, index))}
        <div class="actions start">
          <button class="btn outlined" @click="${() => { this.addActuator('pilot_wire') }}">
            <ha-icon icon="mdi:plus"></ha-icon>${this.t('panel.zone.pilotWire')}
          </button>
          <button class="btn outlined" @click="${() => { this.addActuator('climate') }}">
            <ha-icon icon="mdi:plus"></ha-icon>${this.t('panel.zone.thermostat')}
          </button>
        </div>

        ${errorAlert(this.errors.length > 0 ? this.errors : null)}
        <div class="actions footer">
          <button class="btn text" ?disabled="${this.saving}" @click="${() => { this.done(false) }}">${this.t('panel.cancel')}</button>
          <button class="btn" ?disabled="${this.saving}" @click="${() => { void this.save() }}">
            <ha-icon icon="mdi:content-save-outline"></ha-icon>${this.t('panel.save')}
          </button>
        </div>
      </div>
    `
  }

  static get styles (): CSSResultGroup {
    return css`
      ${style}
      .actuator {
        background-color: var(--card-background-color);
        border: 1px solid var(--hg-border);
        border-radius: var(--hg-radius);
        padding: 8px 12px 12px 12px;
        margin-bottom: 12px;
      }

      .actuator-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 8px;
      }

      .actuator-header > ha-icon {
        color: var(--state-icon-color, var(--primary-color));
      }

      .actuator-header .main {
        flex: 1;
        min-width: 0;
      }

      .actuator-header .title {
        font-weight: 500;
      }

      .actuator-header .subtitle {
        color: var(--hg-muted);
        font-size: 0.8rem;
      }

      .season {
        border-top: 1px solid var(--hg-border);
        padding-top: 4px;
        margin-top: 8px;
      }

      .season-title {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        --mdc-icon-size: 18px;
      }

      .season.on .season-title ha-icon {
        color: var(--primary-color);
      }

      .setpoint {
        display: grid;
        grid-template-columns: 110px 1fr;
        align-items: center;
        gap: 12px;
        margin: 6px 0 6px 26px;
      }

      .setpoint .badge {
        justify-self: start;
        font-size: 0.8rem;
      }

      .hint.small {
        margin: 0 0 4px 26px;
        font-size: 0.8rem;
      }

      .footer {
        border-top: 1px solid var(--hg-border);
        padding-top: 12px;
      }

      @media (max-width: 600px) {
        .setpoint {
          grid-template-columns: 1fr;
          margin-left: 0;
        }
      }
    `
  }
}
