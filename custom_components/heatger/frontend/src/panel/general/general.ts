import { css, type CSSResultGroup, html, LitElement, type PropertyDeclaration, type TemplateResult } from 'lit'
import { type HomeAssistant, type Panel } from 'custom-card-helpers'
import { customElement, property, state } from 'lit/decorators.js'
import './table_zone'
import { localize } from '../../localize/localize'
import { style } from '../../style'
import { heatgerGetZones } from '../websocket/ha-ws'
import {
  heatgerAddZone,
  heatgerRemoveZone
} from '../api/ha-api'
import { type ZoneInfo } from '../websocket/dto/zone-info.dto'
import { type HeatgerZonesTable } from './table_zone'

@customElement('heatger-general-card')
export class HeatgerGeneralCard extends LitElement {
  @property() public hass!: HomeAssistant
  @property() public panel!: Panel
  @property({ type: Boolean, reflect: true }) public narrow!: boolean
  @property() public reload!: () => void
  @state() private error: string | null = null
  @state() private zonesData: Record<string, ZoneInfo> = {}

  firstUpdated (): void {
    this.updateZonesData()
  }

  handleAddZone (event: MouseEvent): void {
    const button = event.target as HTMLElement
    button.blur()
    const form = this.shadowRoot?.querySelector('#add-zone') as HTMLFormElement
    if (form == null) return
    const zone = form.zone.value
    if (zone === '') return

    void heatgerAddZone(this.hass, zone).then(() => {
      this.reload()
    })
  }

  handleDelete (zone: string): void {
    void heatgerRemoveZone(this.hass, zone).then(() => {
      this.reload()
    })
  }

  updateZonesData (): void {
    heatgerGetZones(this.hass)
      .then((r) => {
        this.zonesData = r
        this.updateZoneTable()
        this.requestUpdate()
      })
      .catch((e) => {
        this.error = e.message
        this.requestUpdate()
      })
  }

  requestUpdate (name?: PropertyKey, oldValue?: unknown, options?: PropertyDeclaration): void {
    super.requestUpdate(name, oldValue, options)
    if (name === 'panel') this.updateZonesData()
  }

  updateZoneTable (): void {
    this.error = null
    const zoneTable = this.shadowRoot?.querySelector('heatger-zones-table') as HeatgerZonesTable
    if (zoneTable === null) return
    zoneTable.disabled = true
    zoneTable.requestUpdate()
    // eslint-disable-next-line @typescript-eslint/strict-boolean-expressions
    zoneTable.datas = this.zonesData
    zoneTable.disabled = false
    zoneTable.requestUpdate()
  }

  render (): TemplateResult<1> {
    return html`
      <ha-card header="${localize('panel.general.title', this.hass.language)}">
        ${this.error != null ? html`<div id="error">${this.error}</div>` : ''}
        <div class="card-content">
          <div class="content">
            <h2>Zones</h2>
            <form id="add-zone">
              <div class="flexRow">
                <label for="zone">${localize('panel.general.name', this.hass.language)}</label>
                <input type="text" id="zone" />
              </div>
              <mwc-button @click="${this.handleAddZone}" class="button" id="addZone">
                ${localize('panel.add', this.hass.language)}
              </mwc-button>
            </form>
            <heatger-zones-table
              .hass="${this.hass}"
              .rowClicked="${this.handleDelete.bind(this)}"
            ></heatger-zones-table>
            <h2
          </div>
        </div>
      </ha-card>
    `
  }

  static get styles (): CSSResultGroup {
    return css`
      ${style}
      ha-tab-bar {
        display: flex;
        width: 100%;
      }

      .tab {
        flex-grow: 1;
        text-align: center;
        color: var(--mdc-theme-primary, #6200ee);
      }

      #error {
        background-color: red;
        color: white;
        padding: 3px;
        margin-bottom: 10px;
      }
    `
  }
}
