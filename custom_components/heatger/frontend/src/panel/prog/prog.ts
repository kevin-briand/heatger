import { css, type CSSResultGroup, html, LitElement, type PropertyDeclaration, type TemplateResult } from 'lit';
import { type HomeAssistant, type Panel } from 'custom-card-helpers'
import { customElement, property, state } from 'lit/decorators.js'
import { type Prog } from '../api/prog/dto/prog'
import './table_prog'
import { type HeatgerProgTable } from './table_prog'
import { localize } from '../../localize/localize'
import { style } from '../../style'
import { heatgerGetZones } from '../websocket/ha-ws'
import { heatgerAddProg, heatgerRemoveAllProg, heatgerRemoveProg } from '../api/ha-api'
import { progToUTC } from '../../utils/convert/convert'
import { type ZoneInfo } from '../websocket/dto/zone-info.dto'

@customElement('heatger-prog-card')
export class HeatgerProgCard extends LitElement {
  @property() public hass!: HomeAssistant
  @property() public panel!: Panel
  @property({ type: Boolean, reflect: true }) public narrow!: boolean
  @property() public reload!: () => void
  @state() private error: string | null = null
  @state() private currentTab: number = 0
  @state() private zonesData: Record<string, ZoneInfo> = {}

  firstUpdated (): void {
    this.updateZonesData()
    this.switchTab(0)
  }

  switchTab (tab: number): void {
    this.currentTab = tab
    this.updateProgTable(tab + 1)
  }

  handleAdd (event: MouseEvent): void {
    const button = event.target as HTMLElement
    button.blur()
    const form = this.shadowRoot?.querySelector('form')
    if (form == null) return
    const selectedDays: number[] = []
    const daysOptions = form.days.options as HTMLOptionElement[]
    for (let i = 0; i < daysOptions.length; i++) {
      if (daysOptions[i].selected) {
        selectedDays.push(i)
      }
    }
    const time = form.time.value
    const state = parseInt(form.state.value)
    const zone = parseInt(form.zone.value)
    if (selectedDays.length === 0 || time === '') return

    const progs: Prog[] = []
    selectedDays.forEach((day) => {
      progs.push(progToUTC({ day, hour: time, state }))
    })
    void heatgerAddProg(this.hass, `zone${zone}`, progs).then(() => {
      this.updateZonesData()
    })
  }

  handleDelete (prog: Prog): void {
    const zoneNumber = this.currentTab + 1
    void heatgerRemoveProg(this.hass, `zone${zoneNumber}`, progToUTC(prog)).then(() => {
      this.updateZonesData()
    })
  }

  handleDeleteAll (event: MouseEvent): void {
    const button = event.target as HTMLElement
    button.blur()
    const zoneNumber = this.currentTab + 1
    void heatgerRemoveAllProg(this.hass, `zone${zoneNumber}`).then(() => {
      this.updateZonesData()
    })
  }

  updateZonesData (): void {
    heatgerGetZones(this.hass).then((r) => {
      this.zonesData = r
      this.requestUpdate()
      this.updateProgTable(this.currentTab + 1)
    }).catch((e) => {
      this.error = e.message
      this.requestUpdate()
    })
  }

  updateProgTable (zoneId: number): void {
    this.error = null
    const progTable = this.shadowRoot?.querySelector('heatger-prog-table') as HeatgerProgTable
    if (progTable === null) return
    progTable.disabled = true
    progTable.requestUpdate()
    // eslint-disable-next-line @typescript-eslint/strict-boolean-expressions
    progTable.datas = this.zonesData[`zone${zoneId}`] ? this.zonesData[`zone${zoneId}`].prog : []
    progTable.disabled = false
    progTable.requestUpdate()
  }

  requestUpdate (name?: PropertyKey, oldValue?: unknown, options?: PropertyDeclaration): void {
    super.requestUpdate(name, oldValue, options)
    if (name === 'panel') this.updateZonesData()
  }

  render (): TemplateResult<1> {
    return html`
      <ha-card header="Prog">
        ${this.error != null ? html`<div id="error">${this.error}</div>` : ''}
        <div class="card-content">
          <div class="content">
            <form>
              <div class="flexRow">
                <label for="days">${localize('panel.prog.selectDays', this.hass.language)}</label>
                <select name="days" id="days" multiple>
                  <option value="0">${localize('dayOfWeek.monday', this.hass.language)}</option>
                  <option value="1">${localize('dayOfWeek.tuesday', this.hass.language)}</option>
                  <option value="2">${localize('dayOfWeek.wednesday', this.hass.language)}</option>
                  <option value="3">${localize('dayOfWeek.thursday', this.hass.language)}</option>
                  <option value="4">${localize('dayOfWeek.friday', this.hass.language)}</option>
                  <option value="5">${localize('dayOfWeek.saturday', this.hass.language)}</option>
                  <option value="6">${localize('dayOfWeek.sunday', this.hass.language)}</option>
                </select>
              </div>
              <div class="flexRow">
                <label for="time">${localize('panel.prog.setTime', this.hass.language)}</label>
                <input type="time" name="time" id="time" />
              </div>
              <div class="flexRow">
                <label for="state">${localize('panel.prog.setState', this.hass.language)}</label>
                <select name="state" id="state">
                  <option value="0">${localize('state.comfort', this.hass.language)}</option>
                  <option value="1">${localize('state.eco', this.hass.language)}</option>
                </select>
              </div>
              <div class="flexRow">
                <label for="zone">${localize('zone', this.hass.language)}</label>
                <select name="zone" id="zone">
                  <option value="1">${localize('zone', this.hass.language)} 1</option>
                  <option value="2">${localize('zone', this.hass.language)} 2</option>
                </select>
              </div>
              <div class="flexRow flexRow-center">
                <mwc-button @click="${this.handleAdd}" class="button" id="add">
                  ${localize('panel.add', this.hass.language)}
                </mwc-button>
                <mwc-button @click="${this.handleDeleteAll}" class="button" id="deleteAll">
                  ${localize('panel.deleteAll', this.hass.language)}
                </mwc-button>
              </div>
            </form>

            <ha-tab-bar>
              ${Object.keys(this.zonesData ?? {}).map((zone, index) => {
                return html`<mwc-button
                  class="tab"
                  @click="${() => {
                    this.switchTab(index)
                  }}"
                >
                  ${localize('zone', this.hass.language)} ${index + 1} (${this.zonesData[zone].name})</mwc-button
                >`
              })}
            </ha-tab-bar>
            <heatger-prog-table .hass="${this.hass}" .rowClicked="${this.handleDelete.bind(this)}"></heatger-prog-table>
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
