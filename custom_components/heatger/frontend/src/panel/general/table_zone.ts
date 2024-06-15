import { type CSSResultGroup, html, LitElement, type TemplateResult } from 'lit'
import { customElement, property } from 'lit/decorators.js'
import { localize } from '../../localize/localize'
import { type HomeAssistant } from 'custom-card-helpers'
import { style } from '../../style'
import { type ZoneInfo } from '../websocket/dto/zone-info.dto'

@customElement('heatger-zones-table')
export class HeatgerZonesTable extends LitElement {
  @property() public hass!: HomeAssistant
  @property() public disabled: boolean = false
  @property() public rowClicked!: (zone: string) => void
  @property({ type: Object }) public datas!: Record<string, ZoneInfo>

  addRow (id: string, data: ZoneInfo): TemplateResult<1> {
    return html`
      <tr>
        <td>${data.name}</td>
        <td>${id}</td>
        <td>
          <mwc-button
            @click="${(event: MouseEvent) => {
              this.handleDelete(event, data.name)
            }}"
            class="button"
            id="delete"
            .disabled="${this.disabled}"
          >
            ${localize('panel.delete', this.hass.language)}
          </mwc-button>
        </td>
      </tr>
    `
  }

  handleDelete (event: MouseEvent, data: string): void {
    const button = event.target as HTMLElement
    button.blur()
    this.rowClicked(data)
  }

  render (): TemplateResult<1> {
    if (this.datas === undefined) return html``
    return html`
      <div>
        <table>
          <thead>
            <tr>
              <td>${localize('panel.user.name', this.hass.language)}</td>
              <td>${localize('panel.user.id', this.hass.language)}</td>
              <td></td>
            </tr>
          </thead>
          <tbody>
            ${Object.keys(this.datas).map((value) => {
              return this.addRow(value, this.datas[value])
            })}
          </tbody>
        </table>
      </div>
    `
  }

  static get styles (): CSSResultGroup {
    return style
  }
}
