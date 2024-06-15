import { type CSSResultGroup, html, LitElement, type TemplateResult } from 'lit'
import { customElement, property } from 'lit/decorators.js'
import { localize } from '../../localize/localize'
import { type HomeAssistant } from 'custom-card-helpers'
import { style } from '../../style'

@customElement('heatger-users-table')
export class HeatgerUsersTable extends LitElement {
  @property() public hass!: HomeAssistant
  @property() public disabled: boolean = false
  @property() public rowClicked!: (prog: string) => void
  @property({ type: Array }) public datas!: string[]

  addRow (data: string): TemplateResult<1> {
    if (data === '') return html``
    return html`
            <tr>
                <td>${this.hass.states[data].attributes.friendly_name}</td>
                <td>${data}</td>
                <td><mwc-button @click='${(event: MouseEvent) => { this.handleDelete(event, data) }}' class="button" id="delete" .disabled="${this.disabled}">
                    ${localize('panel.delete', this.hass.language)}
                </mwc-button></td>
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
                    ${this.datas.map((value) => {
                        return this.addRow(value)
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
