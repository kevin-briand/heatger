import { css, type CSSResultGroup, html, LitElement, nothing, type TemplateResult } from 'lit'
import { type HomeAssistant, type Panel } from 'custom-card-helpers'
import { customElement, property, state } from 'lit/decorators.js'
import { localize } from '../../localize/localize'
import { style } from '../../style'
import { heatgerGetSeason } from '../websocket/ha-ws'
import { SEASONS, type SeasonInfo, type SeasonKey } from '../types'
import { errorAlert, SEASON_ICONS } from '../ui'

@customElement('heatger-season-card')
export class HeatgerSeasonCard extends LitElement {
  @property({ attribute: false }) public hass!: HomeAssistant
  @property({ attribute: false }) public panel!: Panel
  @property({ type: Boolean, reflect: true }) public narrow!: boolean
  @property({ attribute: false }) public reload!: () => void
  @state() private season: SeasonInfo | null = null
  @state() private error: string | null = null
  @state() private programming = false
  @state() private programSeason: SeasonKey = 'stop'
  @state() private programNext: SeasonKey = 'heating'
  @state() private programUntil = ''

  firstUpdated (): void {
    this.updateData()
  }

  private t (key: string): string {
    return localize(key, this.hass.language)
  }

  updateData (): void {
    heatgerGetSeason(this.hass).then((season) => {
      this.season = season
      this.error = null
    }).catch((e: Error) => { this.error = e.message })
  }

  /** read the data again (called by the panel after a reload of heatger) */
  refresh (): void {
    this.updateData()
  }

  private setSeason (data: Record<string, string>): void {
    this.hass.callService('heatger', 'set_season', data).then(() => {
      this.updateData()
      this.reload()
    }).catch((e: Error) => { this.error = e.message })
  }

  private program (): void {
    if (this.programUntil === '') {
      this.error = this.t('season.missingDate')
      return
    }
    this.programming = false
    this.setSeason({ season: this.programSeason, until: this.programUntil, next: this.programNext })
  }

  private formatDate (value: string): string {
    return new Date(value).toLocaleString(this.hass.language, {
      weekday: 'long', day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit'
    })
  }

  private seasonSelector (selected: SeasonKey, onSelect: (season: SeasonKey) => void): TemplateResult<1> {
    return html`
      <div class="segmented">
        ${SEASONS.map((season) => html`
          <button class="${season === selected ? 'selected' : ''}" @click="${() => { onSelect(season) }}">
            <ha-icon icon="${SEASON_ICONS[season]}"></ha-icon>${this.t(`season.${season}`)}
          </button>`)}
      </div>`
  }

  private renderProgramForm (): TemplateResult<1> {
    return html`
      <div class="program">
        <div class="field">
          <span class="label">${this.t('season.season')}</span>
          ${this.seasonSelector(this.programSeason, (season) => { this.programSeason = season })}
        </div>
        <div class="field">
          <label for="program-until">${this.t('season.untilDate')}</label>
          <div class="value">
            <input type="datetime-local" id="program-until" .value="${this.programUntil}"
              @change="${(e: Event) => { this.programUntil = (e.target as HTMLInputElement).value }}"/>
          </div>
        </div>
        <div class="field">
          <span class="label">${this.t('season.thenSeason')}</span>
          ${this.seasonSelector(this.programNext, (season) => { this.programNext = season })}
        </div>
        <div class="actions">
          <button class="btn text" @click="${() => { this.programming = false }}">${this.t('panel.cancel')}</button>
          <button class="btn" @click="${this.program}">${this.t('season.apply')}</button>
        </div>
      </div>`
  }

  render (): TemplateResult<1> {
    const season = this.season
    return html`
      <ha-card>
        <div class="card-content">
          ${errorAlert(this.error)}
          ${season === null
            ? nothing
            : html`
              ${this.seasonSelector(season.season, (value) => { if (value !== season.season) this.setSeason({ season: value }) })}
              <p class="hint center">${this.t(`season.hint_${season.season}`)}</p>
              ${season.until !== null
                ? html`
                  <div class="scheduled">
                    <ha-icon icon="mdi:calendar-clock"></ha-icon>
                    <div class="grow">
                      ${this.t('season.until')} <b>${this.formatDate(season.until)}</b>,
                      ${this.t('season.then')} <b>${this.t(`season.${season.next}`).toLowerCase()}</b>
                    </div>
                    <button class="btn text danger" @click="${() => { this.setSeason({ season: season.season }) }}">
                      ${this.t('season.cancelEnd')}
                    </button>
                  </div>`
                : nothing}
              ${this.programming
                ? this.renderProgramForm()
                : html`
                  <div class="actions">
                    <button class="btn outlined" @click="${() => { this.programming = true }}">
                      <ha-icon icon="mdi:calendar-plus"></ha-icon>${this.t('season.program')}
                    </button>
                  </div>`}`}
        </div>
      </ha-card>
    `
  }

  static get styles (): CSSResultGroup {
    return css`
      ${style}
      .center {
        text-align: center;
        margin-top: 12px;
      }

      .grow {
        flex: 1;
      }

      .scheduled {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 8px 8px 8px 12px;
        border-radius: var(--hg-radius);
        background-color: var(--hg-field-bg);
        font-size: 0.9rem;
        --mdc-icon-size: 20px;
      }

      .scheduled ha-icon {
        color: var(--primary-color);
      }

      .program {
        margin-top: 16px;
        padding-top: 16px;
        border-top: 1px solid var(--hg-border);
      }
    `
  }
}
