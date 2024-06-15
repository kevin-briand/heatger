import { type CSSResultGroup, html, LitElement, type TemplateResult } from 'lit'
import { customElement, property } from 'lit/decorators.js'
import { type Prog } from '../api/prog/dto/prog'
import { dayToStr, orderToStr, progFromUTC } from '../../utils/convert/convert';
import { localize } from '../../localize/localize'
import { type HomeAssistant } from 'custom-card-helpers'
import { style } from '../../style'

@customElement('heatger-prog-table')
export class HeatgerProgTable extends LitElement {
  @property() public hass!: HomeAssistant
  @property() public disabled: boolean = false
  @property() public rowClicked!: (prog: Prog) => void
  @property({ type: Array }) public datas!: Prog[]

  addRow (data: Prog): TemplateResult<1> {
    return html`
            <tr>
                <td>${dayToStr(data.day, this.hass.language)}</td>
                <td>${data.hour}</td>
                <td>${orderToStr(data.state, this.hass.language)}</td>
                <td><mwc-button @click='${(event: MouseEvent) => { this.handleDelete(event, data) }}' class="button" id="delete" .disabled="${this.disabled}">
                    ${localize('panel.delete', this.hass.language)}
                </mwc-button></td>
            </tr>
        `
  }

  handleDelete (event: MouseEvent, data: Prog): void {
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
                        <td>${localize('panel.prog.day', this.hass.language)}</td>
                        <td>${localize('panel.prog.time', this.hass.language)}</td>
                        <td>${localize('panel.prog.state', this.hass.language)}</td>
                        <td></td>
                    </tr>
                    </thead>
                    <tbody>
                    ${this.datas.map((value) => {
                        return this.addRow(progFromUTC(value))
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
