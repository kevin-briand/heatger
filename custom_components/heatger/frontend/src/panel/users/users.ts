import { type CSSResultGroup, html, LitElement, PropertyDeclaration, type TemplateResult } from 'lit';
import { type HomeAssistant, type Panel } from 'custom-card-helpers'
import { customElement, property, state } from 'lit/decorators.js'
import './table_users'
import { type HeatgerUsersTable } from './table_users'
import { localize } from '../../localize/localize'
import { style } from '../../style'
import { heatgerGetAvailablePersons, heatgerGetSelectedPersons } from '../websocket/ha-ws'
import { type HassEntityBase } from 'home-assistant-js-websocket'
import { heatgerAddUser, heatgerRemoveUser } from '../api/ha-api';

@customElement('heatger-users-card')
export class HeatgerUsersCard extends LitElement {
  @property() public hass!: HomeAssistant
  @property() public panel!: Panel
  @property({ type: Boolean, reflect: true }) public narrow!: boolean
  @property() public reload!: () => void
  @state() private error: string | null = null
  private availablePersons: HassEntityBase[] = []
  private selectedPersons: string[] = []

  firstUpdated (): void {
    void this.updateData()
  }

  async updateData (): Promise<void> {
    this.availablePersons = await heatgerGetAvailablePersons(this.hass)
    this.selectedPersons = await heatgerGetSelectedPersons(this.hass)
    this.updateUsersTable()
    this.requestUpdate()
  }

  handleAdd (event: MouseEvent): void {
    const button = event.target as HTMLElement
    button.blur()
    const form = this.shadowRoot?.querySelector('form')
    if (form == null) return
    const user = form.availablePersons.value
    if (user === '') return
    void heatgerAddUser(this.hass, user).then(() => { void this.updateData() })
  }

  handleDelete (user: string): void {
    if (user === '') return
    void heatgerRemoveUser(this.hass, user).then(() => { void this.updateData() })
  }

  updateUsersTable (): void {
    this.error = null
    const usersTable = this.shadowRoot?.querySelector('heatger-users-table') as HeatgerUsersTable
    if (usersTable === null) return
    usersTable.disabled = true
    usersTable.requestUpdate()
    usersTable.datas = this.selectedPersons
    usersTable.disabled = false
    usersTable.requestUpdate()
  }

  requestUpdate (name?: PropertyKey, oldValue?: unknown, options?: PropertyDeclaration): void {
    super.requestUpdate(name, oldValue, options)
    if (name === 'panel') void this.updateData()
  }

  render (): TemplateResult<1> {
    return html`
      <ha-card header="${localize('panel.user.title', this.hass.language)}">
        <div class="card-content">
          <div class="content">
            <form>
              <div class="flexRow">
                <label for="availablePersons">${localize('panel.user.person', this.hass.language)}</label>
                <select id="availablePersons">
                  ${this.availablePersons.map(ap => {
                    if (!this.selectedPersons.some(sp => sp === ap.entity_id)) {
                      return html`<option value="${ap.entity_id}">${ap.attributes.friendly_name ?? ap.entity_id}</option>`
                    }
                    return ''
                  })}
                </select>
              </div>
              <div class="flexRow flexRow-center">
                <mwc-button @click='${this.handleAdd}' class="button" id="add">
                  ${localize('panel.add', this.hass.language)}
                </mwc-button>
              </div>
            </form>
            ${this.error}
            <heatger-users-table .hass="${this.hass}" .rowClicked="${this.handleDelete.bind(this)}"></heatger-users-table>
          </div>
        </div>
      </ha-card>      
    `
  }

  static get styles (): CSSResultGroup {
    return style
  }
}
