import { css, type CSSResultGroup, html, LitElement, nothing, type TemplateResult } from 'lit'
import { type HomeAssistant, type Panel } from 'custom-card-helpers'
import { customElement, property, state } from 'lit/decorators.js'
import { localize } from '../../localize/localize'
import { style } from '../../style'
import { heatgerGetConfig } from '../websocket/ha-ws'
import { heatgerAddProg, heatgerCopyProg, heatgerRemoveAllProg, heatgerRemoveProg } from '../api/ha-api'
import { PROGRAMS, type ProgramKey, type ScheduleItem, type ZoneConfig } from '../types'
import { errorAlert, STATE_ICONS } from '../ui'

const DAY_KEYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
const PROGRAM_ICONS: Record<ProgramKey, string> = { winter: 'mdi:snowflake', summer: 'mdi:white-balance-sunny' }
const STATE_CLASSES: Record<number, string> = { 0: 'comfort', 1: 'eco' }
const MINUTES_PER_DAY = 24 * 60

const minutesOf = (hour: string): number => {
  const [h, m] = hour.split(':').map(Number)
  return h * 60 + m
}

interface Segment { start: number, end: number, state: number | null }

/** segments of the day (minutes), the state at midnight is the one of the last change before */
export const daySegments = (schedules: ScheduleItem[], day: number): Segment[] => {
  const sorted = [...schedules].sort((a, b) => (a.day * MINUTES_PER_DAY + minutesOf(a.hour)) - (b.day * MINUTES_PER_DAY + minutesOf(b.hour)))
  if (sorted.length === 0) return [{ start: 0, end: MINUTES_PER_DAY, state: null }]
  const before = sorted.filter((s) => s.day < day)
  let current = (before.length > 0 ? before[before.length - 1] : sorted[sorted.length - 1]).state
  const segments: Segment[] = []
  let start = 0
  for (const schedule of sorted.filter((s) => s.day === day)) {
    const minute = minutesOf(schedule.hour)
    if (minute > start) segments.push({ start, end: minute, state: current })
    current = schedule.state
    start = minute
  }
  segments.push({ start, end: MINUTES_PER_DAY, state: current })
  return segments
}

@customElement('heatger-prog-card')
export class HeatgerProgCard extends LitElement {
  @property({ attribute: false }) public hass!: HomeAssistant
  @property({ attribute: false }) public panel!: Panel
  @property({ type: Boolean, reflect: true }) public narrow!: boolean
  @property({ attribute: false }) public reload!: () => void
  @state() private error: string | null = null
  @state() private zones: ZoneConfig[] = []
  @state() private zoneId: string | null = null
  @state() private program: ProgramKey = 'winter'
  @state() private days: number[] = [0, 1, 2, 3, 4]
  @state() private time = '07:00'
  @state() private newState = 0
  @state() private busy = false

  firstUpdated (): void {
    this.updateZonesData()
  }

  private t (key: string): string {
    return localize(key, this.hass.language)
  }

  private get currentZone (): ZoneConfig | undefined {
    return this.zones.find((zone) => zone.id === this.zoneId)
  }

  private get schedules (): ScheduleItem[] {
    return this.currentZone?.programs[this.program] ?? []
  }

  private run (promise: Promise<unknown>): void {
    this.busy = true
    promise.then(() => {
      this.busy = false
      this.updateZonesData()
    }).catch((e: Error) => {
      this.busy = false
      this.error = e.message
    })
  }

  handleAdd (): void {
    if (this.zoneId === null || this.days.length === 0 || this.time === '') return
    const progs: ScheduleItem[] = [...this.days].sort().map((day) => ({ day, hour: this.time, state: this.newState }))
    this.run(heatgerAddProg(this.hass, this.zoneId, this.program, progs))
  }

  handleDelete (prog: ScheduleItem): void {
    if (this.zoneId === null) return
    this.run(heatgerRemoveProg(this.hass, this.zoneId, this.program, prog))
  }

  handleDeleteAll (): void {
    if (this.zoneId === null || !confirm(this.t('panel.prog.confirmDeleteAll'))) return
    this.run(heatgerRemoveAllProg(this.hass, this.zoneId, this.program))
  }

  handleCopy (): void {
    if (this.zoneId === null) return
    if (this.schedules.length > 0 && !confirm(this.t('panel.prog.confirmCopy'))) return
    const from: ProgramKey = this.program === 'winter' ? 'summer' : 'winter'
    this.run(heatgerCopyProg(this.hass, this.zoneId, from, this.program))
  }

  updateZonesData (): void {
    heatgerGetConfig(this.hass).then((config) => {
      this.error = null
      this.zones = config.zones
      if (this.zones.find((zone) => zone.id === this.zoneId) === undefined) {
        this.zoneId = this.zones.length > 0 ? this.zones[0].id ?? null : null
      }
    }).catch((e: Error) => {
      this.error = e.message
    })
  }

  /** read the data again (called by the panel after a reload of heatger) */
  refresh (): void {
    this.updateZonesData()
  }

  private toggleDay (day: number): void {
    this.days = this.days.includes(day) ? this.days.filter((d) => d !== day) : [...this.days, day]
  }

  // ---- render

  private renderDay (day: number): TemplateResult<1> {
    const schedules = this.schedules
      .filter((schedule) => schedule.day === day)
      .sort((a, b) => minutesOf(a.hour) - minutesOf(b.hour))
    return html`
      <div class="day">
        <div class="day-name">${this.t(`dayOfWeek.${DAY_KEYS[day]}`)}</div>
        <div class="day-content">
          <div class="bar">
            ${daySegments(this.schedules, day).map((segment) => html`
              <div class="segment ${segment.state === null ? 'none' : STATE_CLASSES[segment.state] ?? 'none'}"
                style="left:${segment.start / MINUTES_PER_DAY * 100}%;width:${(segment.end - segment.start) / MINUTES_PER_DAY * 100}%"
                title="${segment.state === null ? '' : this.t(`state.${STATE_CLASSES[segment.state]}`)}"></div>`)}
          </div>
          <div class="chips">
            ${schedules.map((schedule) => html`
              <span class="chip static event ${STATE_CLASSES[schedule.state] ?? ''}">
                <ha-icon icon="${STATE_ICONS[schedule.state] ?? 'mdi:help'}"></ha-icon>
                ${schedule.hour}
                <button class="remove" title="${this.t('panel.delete')}" ?disabled="${this.busy}"
                  @click="${() => { this.handleDelete(schedule) }}"><ha-icon icon="mdi:close"></ha-icon></button>
              </span>`)}
          </div>
        </div>
      </div>`
  }

  private renderAddForm (): TemplateResult<1> {
    const shortcuts: Array<[string, number[]]> = [
      ['panel.prog.weekdays', [0, 1, 2, 3, 4]], ['panel.prog.weekend', [5, 6]], ['panel.prog.everyDay', [0, 1, 2, 3, 4, 5, 6]]
    ]
    return html`
      <div class="add">
        <h3 class="section">${this.t('panel.prog.addTitle')}</h3>
        <div class="field">
          <span class="label">${this.t('panel.prog.selectDays')}</span>
          <div class="value days">
            <div class="chips">
              ${DAY_KEYS.map((key, day) => html`
                <button class="chip ${this.days.includes(day) ? 'selected' : ''}" title="${this.t(`dayOfWeek.${key}`)}"
                  @click="${() => { this.toggleDay(day) }}">${this.t(`dayOfWeek.${key}`).slice(0, 3)}</button>`)}
            </div>
            <div class="shortcuts">
              ${shortcuts.map(([label, days]) => html`
                <button class="btn text" @click="${() => { this.days = [...days] }}">${this.t(label)}</button>`)}
            </div>
          </div>
        </div>
        <div class="field">
          <label for="time">${this.t('panel.prog.setTime')}</label>
          <div class="value">
            <input type="time" id="time" class="time" .value="${this.time}"
              @change="${(e: Event) => { this.time = (e.target as HTMLInputElement).value }}"/>
          </div>
        </div>
        <div class="field">
          <span class="label">${this.t('panel.prog.setState')}</span>
          <div class="segmented compact">
            ${[0, 1].map((value) => html`
              <button class="${this.newState === value ? 'selected' : ''}" @click="${() => { this.newState = value }}">
                <ha-icon icon="${STATE_ICONS[value]}"></ha-icon>${this.t(`state.${STATE_CLASSES[value]}`)}
              </button>`)}
          </div>
        </div>
        <div class="actions">
          <button class="btn" id="add" ?disabled="${this.zoneId === null || this.days.length === 0 || this.busy}"
            @click="${this.handleAdd}"><ha-icon icon="mdi:plus"></ha-icon>${this.t('panel.add')}</button>
        </div>
      </div>`
  }

  render (): TemplateResult<1> {
    const otherProgram: ProgramKey = this.program === 'winter' ? 'summer' : 'winter'
    return html`
      <ha-card>
        <div class="card-content">
          ${errorAlert(this.error)}
          ${this.zones.length === 0
            ? html`<p class="hint">${this.t('panel.prog.noZone')}</p>`
            : html`
              <div class="segmented tabs">
                ${this.zones.map((zone) => html`
                  <button class="${zone.id === this.zoneId ? 'selected' : ''}"
                    @click="${() => { this.zoneId = zone.id ?? null }}">${zone.name}</button>`)}
              </div>
              <div class="program-row">
                <div class="segmented compact">
                  ${PROGRAMS.map((program) => html`
                    <button class="${program === this.program ? 'selected' : ''}" @click="${() => { this.program = program }}">
                      <ha-icon icon="${PROGRAM_ICONS[program]}"></ha-icon>${this.t(`program.${program}`)}
                    </button>`)}
                </div>
                <span class="hint">${this.t(`panel.prog.hint_${this.program}`)}</span>
              </div>

              <div class="week">
                <div class="day scale">
                  <div class="day-name"></div>
                  <div class="day-content ticks">
                    ${[0, 6, 12, 18, 24].map((hour) => html`<span style="left:${hour / 24 * 100}%">${hour}h</span>`)}
                  </div>
                </div>
                ${DAY_KEYS.map((_, day) => this.renderDay(day))}
                ${this.schedules.length === 0 ? html`<p class="hint center">${this.t('panel.prog.empty')}</p>` : nothing}
                <div class="legend">
                  <span><i class="dot comfort"></i>${this.t('state.comfort')}</span>
                  <span><i class="dot eco"></i>${this.t('state.eco')}</span>
                </div>
              </div>

              ${this.renderAddForm()}

              <div class="actions start other">
                <button class="btn text" ?disabled="${this.busy}" @click="${this.handleCopy}">
                  <ha-icon icon="mdi:content-copy"></ha-icon>${this.t(`panel.prog.copy_from_${otherProgram}`)}
                </button>
                <button class="btn text danger" ?disabled="${this.busy || this.schedules.length === 0}" @click="${this.handleDeleteAll}">
                  <ha-icon icon="mdi:delete-sweep-outline"></ha-icon>${this.t('panel.deleteAll')}
                </button>
              </div>`}
        </div>
      </ha-card>
    `
  }

  static get styles (): CSSResultGroup {
    return css`
      ${style}
      .tabs {
        margin-bottom: 12px;
      }

      .program-row {
        display: flex;
        align-items: center;
        gap: 12px;
        flex-wrap: wrap;
        margin-bottom: 16px;
      }

      .program-row .hint {
        margin: 0;
      }

      .center {
        text-align: center;
      }

      .week {
        margin-bottom: 8px;
      }

      .day {
        display: grid;
        grid-template-columns: 90px 1fr;
        gap: 12px;
        align-items: start;
        padding: 6px 0;
      }

      .day + .day {
        border-top: 1px solid var(--hg-border);
      }

      .day.scale {
        padding: 0;
      }

      .day-name {
        font-size: 0.9rem;
        line-height: 14px;
        padding-top: 1px;
      }

      .bar {
        position: relative;
        height: 14px;
        border-radius: 7px;
        overflow: hidden;
        background-color: rgba(127, 127, 127, 0.15);
      }

      .segment {
        position: absolute;
        top: 0;
        bottom: 0;
      }

      .segment.comfort, .dot.comfort {
        background-color: var(--hg-comfort);
      }

      .segment.eco, .dot.eco {
        background-color: var(--hg-eco);
      }

      .ticks {
        position: relative;
        height: 16px;
        font-size: 0.7rem;
        color: var(--hg-muted);
      }

      .ticks span {
        position: absolute;
        transform: translateX(-50%);
      }

      .ticks span:first-child {
        transform: none;
      }

      .ticks span:last-child {
        transform: translateX(-100%);
      }

      .day-content .chips {
        margin-top: 6px;
      }

      .day-content .chips:empty {
        display: none;
      }

      .chip.event {
        height: 26px;
        padding: 0 2px 0 8px;
        gap: 4px;
        font-variant-numeric: tabular-nums;
      }

      .chip.event.comfort ha-icon {
        color: var(--hg-comfort);
      }

      .chip.event.eco ha-icon {
        color: var(--hg-eco);
      }

      .chip .remove {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 20px;
        height: 20px;
        border: none;
        border-radius: 50%;
        background: transparent;
        color: var(--hg-muted);
        cursor: pointer;
        padding: 0;
        --mdc-icon-size: 14px;
      }

      .chip .remove:hover {
        background-color: rgba(127, 127, 127, 0.2);
        color: var(--error-color, #db4437);
      }

      .chip .remove ha-icon {
        color: inherit !important;
      }

      .legend {
        display: flex;
        gap: 16px;
        justify-content: flex-end;
        font-size: 0.8rem;
        color: var(--hg-muted);
        margin-top: 4px;
      }

      .legend span {
        display: inline-flex;
        align-items: center;
        gap: 6px;
      }

      .dot {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
      }

      .add {
        border-top: 1px solid var(--hg-border);
        margin-top: 12px;
        padding-top: 4px;
      }

      .add h3.section:first-child {
        margin-top: 16px;
      }

      .value.days {
        flex-direction: column;
        align-items: flex-start;
        gap: 4px;
      }

      .shortcuts .btn {
        height: 28px;
        font-size: 0.8rem;
      }

      input.time {
        width: 130px;
      }

      .other {
        border-top: 1px solid var(--hg-border);
        padding-top: 8px;
        margin-top: 8px;
      }

      @media (max-width: 600px) {
        .day {
          grid-template-columns: 1fr;
          gap: 4px;
        }

        .day.scale .day-name {
          display: none;
        }
      }
    `
  }
}
