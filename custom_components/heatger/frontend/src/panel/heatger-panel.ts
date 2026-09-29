import { css, html, LitElement, type TemplateResult } from 'lit'
import { type HomeAssistant, type Panel } from 'custom-card-helpers'
import { customElement, property, state } from 'lit/decorators.js'
import './prog/prog'
import './users/users'
import './general/general'
import './season/season'
import './setpoints/setpoints'
import { VERSION } from './consts'
import { localize } from '../localize/localize'

type TabKey = 'season' | 'zones' | 'programs' | 'setpoints' | 'presence'

const TABS: Array<{ key: TabKey, icon: string }> = [
  { key: 'season', icon: 'mdi:calendar-sync' },
  { key: 'zones', icon: 'mdi:home-group' },
  { key: 'programs', icon: 'mdi:calendar-week' },
  { key: 'setpoints', icon: 'mdi:thermometer' },
  { key: 'presence', icon: 'mdi:account-group' }
]
const STORAGE_KEY = 'heatger-panel-tab'

const readTab = (): TabKey => {
  try {
    const saved = window.localStorage.getItem(STORAGE_KEY)
    if (TABS.some((tab) => tab.key === saved)) return saved as TabKey
  } catch (e) {
    // no storage (private window...): first tab
  }
  return 'season'
}

@customElement('heatger-panel')
export class HeatgerPanel extends LitElement {
  @property({ attribute: false }) public hass!: HomeAssistant
  @property({ attribute: false }) public panel!: Panel
  @property({ type: Boolean, reflect: true }) public narrow!: boolean
  @state() private tab: TabKey = readTab()

  private selectTab (tab: TabKey): void {
    this.tab = tab
    try {
      window.localStorage.setItem(STORAGE_KEY, tab)
    } catch (e) {
      // not remembered
    }
  }

  render (): TemplateResult<1> {
    return html`
            <div class="header">
                <div class="toolbar">
                    <ha-menu-button .hass=${this.hass} .narrow=${this.narrow}></ha-menu-button>
                    <div class="main-title">Heatger</div>
                    <div class="version">v${VERSION}</div>
                </div>
                <div class="tabs" role="tablist">
                    ${TABS.map((tab) => html`
                      <button role="tab" class="tab ${tab.key === this.tab ? 'selected' : ''}" aria-selected="${tab.key === this.tab}"
                        title="${localize(`panel.tabs.${tab.key}`, this.hass.language)}"
                        @click="${() => { this.selectTab(tab.key) }}">
                        <ha-icon icon="${tab.icon}"></ha-icon>
                        <span>${localize(`panel.tabs.${tab.key}`, this.hass.language)}</span>
                      </button>`)}
                </div>
            </div>
            <div class="view">
                ${this.getCard()}
            </div>
        `
  }

  /** a change of zone reloads heatger: every card reads its data again */
  reload (): void {
    this.shadowRoot?.querySelectorAll('.card').forEach((el) => {
      (el as HTMLElement & { refresh?: () => void }).refresh?.()
    })
  }

  getCard (): TemplateResult<1> {
    const reload = this.reload.bind(this)
    switch (this.tab) {
      case 'zones':
        return html`<heatger-general-card class="card" .hass=${this.hass} .narrow=${this.narrow} .panel=${this.panel} .reload="${reload}"></heatger-general-card>`
      case 'programs':
        return html`<heatger-prog-card class="card" .hass=${this.hass} .narrow=${this.narrow} .panel=${this.panel} .reload="${reload}"></heatger-prog-card>`
      case 'setpoints':
        return html`<heatger-setpoints-card class="card" .hass=${this.hass} .narrow=${this.narrow} .panel=${this.panel} .reload="${reload}"></heatger-setpoints-card>`
      case 'presence':
        return html`<heatger-users-card class="card" .hass=${this.hass} .narrow=${this.narrow} .panel=${this.panel} .reload="${reload}"></heatger-users-card>`
      default:
        return html`<heatger-season-card class="card" .hass=${this.hass} .narrow=${this.narrow} .panel=${this.panel} .reload="${reload}"></heatger-season-card>`
    }
  }

  static readonly styles = css`
          :host {
            display: block;
            height: 100%;
            overflow-y: auto;
            background-color: var(--primary-background-color);
          }
          .header {
            position: sticky;
            top: 0;
            z-index: 2;
            background-color: var(--app-header-background-color);
            color: var(--app-header-text-color, white);
            border-bottom: var(--app-header-border-bottom, none);
          }
          .toolbar {
            height: var(--header-height, 56px);
            display: flex;
            align-items: center;
            font-size: 20px;
            padding: 0 16px;
            font-weight: 400;
            box-sizing: border-box;
          }
          .main-title {
            margin: 0 0 0 24px;
            line-height: 20px;
            flex-grow: 1;
          }
          .version {
            font-size: 13px;
            opacity: 0.8;
          }
          .tabs {
            display: flex;
            justify-content: center;
            overflow-x: auto;
            scrollbar-width: none;
            padding: 0 8px;
          }
          .tab {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            height: 48px;
            padding: 0 16px;
            border: none;
            border-bottom: 2px solid transparent;
            background: transparent;
            color: inherit;
            opacity: 0.75;
            font: inherit;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            white-space: nowrap;
            --mdc-icon-size: 20px;
          }
          .tab:hover {
            opacity: 1;
          }
          .tab.selected {
            opacity: 1;
            border-bottom-color: var(--app-header-text-color, white);
          }
          @media (max-width: 600px) {
            .tabs {
              justify-content: space-between;
            }
            .tab {
              flex: 1;
              justify-content: center;
              padding: 0 8px;
            }
            .tab span {
              display: none;
            }
          }
          .card {
            display: block;
          }
          .view {
            box-sizing: border-box;
            max-width: 760px;
            margin: 0 auto;
            padding: 16px 16px 32px 16px;
          }
    `
}
