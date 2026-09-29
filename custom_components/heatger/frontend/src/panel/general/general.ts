import { css, type CSSResultGroup, html, LitElement, nothing, type PropertyDeclaration, type TemplateResult } from 'lit'
import { type HomeAssistant, type Panel } from 'custom-card-helpers'
import { customElement, property, state } from 'lit/decorators.js'
import './zone_editor'
import { localize } from '../../localize/localize'
import { style } from '../../style'
import { heatgerDeleteZone, heatgerGetClimateEntities, heatgerGetConfig, heatgerMoveZone } from '../websocket/ha-ws'
import { heatgerAddZone } from '../api/ha-api'
import type { ActuatorConfig, ClimateEntityInfo, ZoneConfig } from '../types'
import { errorAlert, iconButton, infoAlert } from '../ui'

// the integration is reloaded after a change of zone: wait before reading the new state
const RELOAD_DELAY = 2500

@customElement('heatger-general-card')
export class HeatgerGeneralCard extends LitElement {
  @property({ attribute: false }) public hass!: HomeAssistant
  @property({ attribute: false }) public panel!: Panel
  @property({ type: Boolean, reflect: true }) public narrow!: boolean
  @property({ attribute: false }) public reload!: () => void
  @state() private error: string | null = null
  @state() private info: string | null = null
  @state() private zones: ZoneConfig[] = []
  @state() private climates: ClimateEntityInfo[] = []
  @state() private editingId: string | null = null
  @state() private newZone = ''

  firstUpdated (): void {
    this.updateZonesData()
  }

  private t (key: string): string {
    return localize(key, this.hass.language)
  }

  updateZonesData (): void {
    Promise.all([heatgerGetConfig(this.hass), heatgerGetClimateEntities(this.hass)]).then(([config, climates]) => {
      this.error = null
      this.zones = config.zones
      this.climates = climates
    }).catch((e: Error) => {
      this.error = e.message
    })
  }

  /** the integration reloads: refresh every card once it's done */
  private afterReload (): void {
    this.info = this.t('panel.zone.reloading')
    setTimeout(() => {
      this.info = null
      this.reload()
      this.updateZonesData()
    }, RELOAD_DELAY)
  }

  handleAddZone (): void {
    const name = this.newZone.trim()
    if (name === '') return
    heatgerAddZone(this.hass, name).then(() => {
      this.newZone = ''
      this.afterReload()
    }).catch((e: Error) => { this.error = e.message })
  }

  handleDelete (zone: ZoneConfig): void {
    if (zone.id === undefined || !confirm(`${this.t('panel.zone.confirmDelete')} « ${zone.name} » ?`)) return
    heatgerDeleteZone(this.hass, zone.id).then(() => { this.afterReload() })
      .catch((e: Error) => { this.error = e.message })
  }

  handleMove (zone: ZoneConfig, offset: number): void {
    if (zone.id === undefined) return
    heatgerMoveZone(this.hass, zone.id, offset).then(() => { this.afterReload() })
      .catch((e: Error) => { this.error = e.message })
  }

  editDone (saved: boolean): void {
    this.editingId = null
    if (saved) this.afterReload()
  }

  requestUpdate (name?: PropertyKey, oldValue?: unknown, options?: PropertyDeclaration): void {
    super.requestUpdate(name, oldValue, options)
    if (name === 'panel') this.updateZonesData()
  }

  private actuatorChip (actuator: ActuatorConfig): TemplateResult<1> {
    const pilotWire = actuator.type === 'pilot_wire'
    const label = pilotWire
      ? `${this.t('panel.zone.pilotWire')} · ${actuator.output ?? ''}`
      : (actuator.name !== '' ? actuator.name : actuator.entity_id ?? '')
    return html`<span class="badge"><ha-icon icon="${pilotWire ? 'mdi:radiator' : 'mdi:thermostat'}"></ha-icon>${label}</span>`
  }

  private renderZone (zone: ZoneConfig, index: number): TemplateResult<1> {
    const editing = this.editingId !== null && this.editingId === zone.id
    return html`
      <div class="list-item ${zone.enabled ? '' : 'disabled'}">
        <ha-icon icon="mdi:home-thermometer-outline"></ha-icon>
        <div class="main">
          <div class="title">
            ${zone.name}
            ${zone.enabled ? nothing : html`<span class="badge">${this.t('panel.zone.disabled')}</span>`}
          </div>
          <div class="subtitle chips">
            ${zone.actuators.length > 0
              ? zone.actuators.map((actuator) => this.actuatorChip(actuator))
              : html`<span>${this.t('panel.zone.noActuator')}</span>`}
          </div>
        </div>
        <div class="buttons">
          ${iconButton('mdi:arrow-up', this.t('panel.moveUp'), () => { this.handleMove(zone, -1) }, { disabled: index === 0 })}
          ${iconButton('mdi:arrow-down', this.t('panel.moveDown'), () => { this.handleMove(zone, 1) }, { disabled: index === this.zones.length - 1 })}
          ${iconButton(editing ? 'mdi:close' : 'mdi:pencil', this.t(editing ? 'panel.cancel' : 'panel.edit'),
            () => { this.editingId = editing ? null : zone.id ?? null })}
          ${iconButton('mdi:delete-outline', this.t('panel.delete'), () => { this.handleDelete(zone) }, { danger: true })}
        </div>
      </div>
      ${editing
        ? html`<div class="expand">
            <heatger-zone-editor .hass="${this.hass}" .zone="${zone}" .climates="${this.climates}"
              .done="${this.editDone.bind(this)}"></heatger-zone-editor>
          </div>`
        : nothing}
    `
  }

  render (): TemplateResult<1> {
    return html`
      <ha-card>
        <div class="card-content">
          ${errorAlert(this.error)}
          ${infoAlert(this.info)}
          <p class="hint">${this.t('panel.zone.hint')}</p>
          <div class="list">
            ${this.zones.length === 0 ? html`<div class="list-empty">${this.t('panel.zone.empty')}</div>` : nothing}
            ${this.zones.map((zone, index) => this.renderZone(zone, index))}
          </div>
          <div class="add-row">
            <input type="text" id="new-zone" placeholder="${this.t('panel.zone.newZone')}" .value="${this.newZone}"
              @input="${(e: Event) => { this.newZone = (e.target as HTMLInputElement).value }}"
              @keydown="${(e: KeyboardEvent) => { if (e.key === 'Enter') this.handleAddZone() }}"/>
            <button class="btn" ?disabled="${this.newZone.trim() === ''}" @click="${this.handleAddZone}">
              <ha-icon icon="mdi:plus"></ha-icon>${this.t('panel.add')}
            </button>
          </div>
        </div>
      </ha-card>
    `
  }

  static get styles (): CSSResultGroup {
    return css`
      ${style}
      .list-item.disabled .title, .list-item.disabled > ha-icon {
        opacity: 0.55;
      }

      .subtitle.chips {
        margin-top: 6px;
      }

      .add-row {
        display: flex;
        gap: 8px;
        align-items: center;
        margin-top: 12px;
      }

      .add-row input {
        flex: 1;
      }
    `
  }
}
