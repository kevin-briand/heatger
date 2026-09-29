import { css, type CSSResultGroup, html, LitElement, nothing, type TemplateResult } from 'lit'
import { type HomeAssistant, type Panel } from 'custom-card-helpers'
import { customElement, property, state } from 'lit/decorators.js'
import { localize } from '../../localize/localize'
import { style } from '../../style'
import { heatgerGetAvailablePersons, heatgerGetSelectedPersons } from '../websocket/ha-ws'
import { type HassEntityBase } from 'home-assistant-js-websocket'
import { heatgerAddUser, heatgerRemoveUser } from '../api/ha-api'
import { errorAlert, iconButton } from '../ui'

@customElement('heatger-users-card')
export class HeatgerUsersCard extends LitElement {
  @property({ attribute: false }) public hass!: HomeAssistant
  @property({ attribute: false }) public panel!: Panel
  @property({ type: Boolean, reflect: true }) public narrow!: boolean
  @property({ attribute: false }) public reload!: () => void
  @state() private error: string | null = null
  @state() private availablePersons: HassEntityBase[] = []
  @state() private selectedPersons: string[] = []
  @state() private toAdd = ''

  firstUpdated (): void {
    void this.updateData()
  }

  private t (key: string): string {
    return localize(key, this.hass.language)
  }

  async updateData (): Promise<void> {
    try {
      const [available, selected] = await Promise.all([heatgerGetAvailablePersons(this.hass), heatgerGetSelectedPersons(this.hass)])
      this.availablePersons = available
      this.selectedPersons = selected.filter((user) => user !== '')
      this.error = null
    } catch (e) {
      this.error = (e as Error).message
    }
  }

  private get candidates (): HassEntityBase[] {
    return this.availablePersons.filter((person) => !this.selectedPersons.includes(person.entity_id))
  }

  handleAdd (): void {
    const user = this.toAdd !== '' ? this.toAdd : this.candidates[0]?.entity_id ?? ''
    if (user === '') return
    heatgerAddUser(this.hass, user).then(() => {
      this.toAdd = ''
      void this.updateData()
    }).catch((e: Error) => { this.error = e.message })
  }

  handleDelete (user: string): void {
    heatgerRemoveUser(this.hass, user).then(() => { void this.updateData() })
      .catch((e: Error) => { this.error = e.message })
  }

  /** read the data again (called by the panel after a reload of heatger) */
  refresh (): void {
    void this.updateData()
  }

  private renderUser (user: string): TemplateResult<1> {
    const entity = this.hass.states[user]
    const name = String(entity?.attributes.friendly_name ?? user)
    const home = entity?.state === 'home'
    return html`
      <div class="list-item">
        <ha-icon icon="${home ? 'mdi:account' : 'mdi:account-outline'}"></ha-icon>
        <div class="main">
          <div class="title">${name}
            ${entity !== undefined
              ? html`<span class="badge ${home ? 'home' : ''}">${this.t(home ? 'panel.user.home' : 'panel.user.away')}</span>`
              : nothing}
          </div>
          <div class="subtitle">${user}</div>
        </div>
        <div class="buttons">
          ${iconButton('mdi:delete-outline', this.t('panel.delete'), () => { this.handleDelete(user) }, { danger: true })}
        </div>
      </div>`
  }

  render (): TemplateResult<1> {
    const candidates = this.candidates
    return html`
      <ha-card>
        <div class="card-content">
          ${errorAlert(this.error)}
          <p class="hint">${this.t('panel.user.hint')}</p>
          <div class="list">
            ${this.selectedPersons.length === 0 ? html`<div class="list-empty">${this.t('panel.user.empty')}</div>` : nothing}
            ${this.selectedPersons.map((user) => this.renderUser(user))}
          </div>
          ${candidates.length > 0
            ? html`
              <div class="add-row">
                <select id="availablePersons" @change="${(e: Event) => { this.toAdd = (e.target as HTMLSelectElement).value }}">
                  ${candidates.map((person) => html`
                    <option value="${person.entity_id}" ?selected="${person.entity_id === this.toAdd}">
                      ${person.attributes.friendly_name ?? person.entity_id}</option>`)}
                </select>
                <button class="btn" id="add" @click="${this.handleAdd}"><ha-icon icon="mdi:plus"></ha-icon>${this.t('panel.add')}</button>
              </div>`
            : nothing}
        </div>
      </ha-card>
    `
  }

  static get styles (): CSSResultGroup {
    return css`
      ${style}
      .add-row {
        display: flex;
        gap: 8px;
        align-items: center;
        margin-top: 12px;
      }

      .add-row select {
        flex: 1;
      }

      .badge.home {
        background-color: color-mix(in srgb, var(--success-color, #43a047) 20%, transparent);
        color: var(--success-color, #43a047);
      }
    `
  }
}
