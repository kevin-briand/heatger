import { css } from 'lit'

/**
 * Shared look of the panel, based on the variables of the Home Assistant theme (light and dark).
 * Native inputs are used (always available), styled like the fields of Home Assistant.
 */
export const style = css`
  :host {
    --hg-radius: 8px;
    --hg-gap: 12px;
    --hg-field-bg: var(--input-fill-color, var(--secondary-background-color, rgba(127, 127, 127, 0.08)));
    --hg-border: var(--divider-color, rgba(127, 127, 127, 0.3));
    --hg-comfort: var(--state-climate-heat-color, #ff8100);
    --hg-eco: var(--state-climate-cool-color, #2b9af9);
    --hg-muted: var(--secondary-text-color);
    color: var(--primary-text-color);
  }

  ha-card {
    display: block;
    margin: 0 0 16px 0;
  }

  .card-header-row {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 16px 16px 0 16px;
  }

  .card-header-row h1 {
    margin: 0;
    font-size: 20px;
    font-weight: 400;
    flex: 1;
  }

  .card-header-row ha-icon {
    color: var(--state-icon-color, var(--primary-color));
  }

  .card-content {
    padding: 16px;
  }

  .hint {
    color: var(--hg-muted);
    font-size: 0.875rem;
    line-height: 1.4;
    margin: 0 0 12px 0;
  }

  h3.section {
    font-size: 0.8rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--hg-muted);
    margin: 20px 0 8px 0;
  }

  h3.section:first-child {
    margin-top: 0;
  }

  /* ---- form fields: label on the left, input on the right (stacked when narrow) */
  .field {
    display: grid;
    grid-template-columns: 170px 1fr;
    align-items: center;
    gap: var(--hg-gap);
    min-height: 40px;
    margin-bottom: 8px;
  }

  .field > label, .field > .label {
    color: var(--primary-text-color);
    font-size: 0.95rem;
  }

  .field > .value {
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
  }

  @media (max-width: 600px) {
    .field {
      grid-template-columns: 1fr;
      gap: 4px;
    }
  }

  input[type="text"], input[type="number"], input[type="time"], input[type="datetime-local"], select {
    box-sizing: border-box;
    height: 40px;
    width: 100%;
    min-width: 0;
    padding: 0 12px;
    font: inherit;
    font-size: 0.95rem;
    color: var(--primary-text-color);
    background-color: var(--hg-field-bg);
    border: 1px solid var(--hg-border);
    border-radius: var(--hg-radius);
    outline: none;
    color-scheme: light dark;
  }

  select option {
    background-color: var(--card-background-color);
    color: var(--primary-text-color);
  }

  input:focus, select:focus {
    border-color: var(--primary-color);
    box-shadow: 0 0 0 1px var(--primary-color);
  }

  input[type="number"] {
    width: 90px;
    flex: 0 0 auto;
  }

  .unit {
    color: var(--hg-muted);
  }

  /* ---- buttons */
  button {
    font: inherit;
  }

  .btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    height: 36px;
    padding: 0 16px;
    border-radius: 18px;
    border: none;
    cursor: pointer;
    font-size: 0.9rem;
    font-weight: 500;
    background-color: var(--primary-color);
    color: var(--text-primary-color, #fff);
    white-space: nowrap;
  }

  .btn.outlined {
    background: transparent;
    color: var(--primary-color);
    border: 1px solid var(--hg-border);
  }

  .btn.text {
    background: transparent;
    color: var(--primary-color);
    padding: 0 10px;
  }

  .btn.danger {
    color: var(--error-color, #db4437);
  }

  .btn:hover {
    filter: brightness(1.08);
  }

  .btn.outlined:hover, .btn.text:hover {
    background-color: rgba(var(--rgb-primary-color, 3, 169, 244), 0.1);
  }

  .btn[disabled] {
    opacity: 0.45;
    cursor: default;
    filter: none;
  }

  .btn ha-icon {
    --mdc-icon-size: 18px;
  }

  .icon-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    border-radius: 50%;
    border: none;
    background: transparent;
    color: var(--hg-muted);
    cursor: pointer;
    padding: 0;
    flex: 0 0 auto;
    --mdc-icon-size: 20px;
  }

  .icon-btn:hover {
    background-color: rgba(127, 127, 127, 0.15);
    color: var(--primary-text-color);
  }

  .icon-btn.danger:hover {
    color: var(--error-color, #db4437);
  }

  .icon-btn[disabled] {
    opacity: 0.3;
    cursor: default;
    background: transparent;
  }

  .actions {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
    margin-top: 16px;
  }

  .actions.start {
    justify-content: flex-start;
  }

  /* ---- segmented control (tabs, season, state) */
  .segmented {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    padding: 4px;
    border-radius: 12px;
    background-color: var(--hg-field-bg);
    border: 1px solid var(--hg-border);
  }

  .segmented button {
    flex: 1 1 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    min-height: 34px;
    padding: 0 12px;
    border: none;
    border-radius: 8px;
    background: transparent;
    color: var(--hg-muted);
    cursor: pointer;
    font-size: 0.9rem;
    white-space: nowrap;
    --mdc-icon-size: 18px;
  }

  .segmented button:hover {
    color: var(--primary-text-color);
  }

  .segmented button.selected {
    background-color: rgba(var(--rgb-primary-color, 3, 169, 244), 0.18);
    color: var(--primary-text-color);
    font-weight: 500;
  }

  .segmented button.selected ha-icon {
    color: var(--primary-color);
  }

  .segmented.compact {
    display: inline-flex;
    justify-self: start;
  }

  .segmented.compact button {
    flex: 0 0 auto;
  }

  /* ---- chips */
  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .chip {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    height: 28px;
    padding: 0 10px;
    border-radius: 14px;
    border: 1px solid var(--hg-border);
    background: transparent;
    color: var(--primary-text-color);
    font-size: 0.85rem;
    cursor: pointer;
    --mdc-icon-size: 16px;
  }

  .chip.selected {
    background-color: var(--primary-color);
    border-color: var(--primary-color);
    color: var(--text-primary-color, #fff);
  }

  .chip.static {
    cursor: default;
  }

  .badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 0.75rem;
    font-weight: 500;
    background-color: rgba(127, 127, 127, 0.18);
    color: var(--hg-muted);
    --mdc-icon-size: 14px;
  }

  .badge.comfort {
    background-color: color-mix(in srgb, var(--hg-comfort) 20%, transparent);
    color: var(--hg-comfort);
  }

  .badge.eco {
    background-color: color-mix(in srgb, var(--hg-eco) 20%, transparent);
    color: var(--hg-eco);
  }

  /* ---- lists */
  .list {
    border: 1px solid var(--hg-border);
    border-radius: var(--hg-radius);
    overflow: hidden;
  }

  .list-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 8px 8px 8px 16px;
    min-height: 48px;
  }

  .list-item + .list-item, .list-item + .expand, .expand + .list-item {
    border-top: 1px solid var(--hg-border);
  }

  .list-item > ha-icon {
    color: var(--state-icon-color, var(--primary-color));
    flex: 0 0 auto;
  }

  .list-item .main {
    flex: 1;
    min-width: 0;
  }

  .list-item .title {
    font-size: 1rem;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .list-item .subtitle {
    color: var(--hg-muted);
    font-size: 0.85rem;
    margin-top: 2px;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .list-item .buttons {
    display: flex;
    align-items: center;
    flex: 0 0 auto;
  }

  .list-empty {
    padding: 16px;
    color: var(--hg-muted);
    text-align: center;
    font-size: 0.9rem;
  }

  .expand {
    background-color: var(--hg-field-bg);
    padding: 16px;
  }

  /* ---- switch */
  .switch {
    position: relative;
    display: inline-block;
    width: 36px;
    height: 20px;
    flex: 0 0 auto;
  }

  .switch input {
    opacity: 0;
    width: 0;
    height: 0;
  }

  .switch .slider {
    position: absolute;
    inset: 0;
    cursor: pointer;
    border-radius: 10px;
    background-color: rgba(127, 127, 127, 0.45);
    transition: background-color 0.2s;
  }

  .switch .slider::before {
    content: '';
    position: absolute;
    width: 16px;
    height: 16px;
    left: 2px;
    top: 2px;
    border-radius: 50%;
    background-color: #fff;
    transition: transform 0.2s;
  }

  .switch input:checked + .slider {
    background-color: var(--primary-color);
  }

  .switch input:checked + .slider::before {
    transform: translateX(16px);
  }

  .switch-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    min-height: 40px;
    cursor: pointer;
  }

  /* ---- messages */
  .alert {
    display: flex;
    gap: 10px;
    align-items: flex-start;
    padding: 10px 12px;
    border-radius: var(--hg-radius);
    margin: 0 0 12px 0;
    font-size: 0.9rem;
    --mdc-icon-size: 20px;
  }

  .alert.error {
    background-color: color-mix(in srgb, var(--error-color, #db4437) 15%, transparent);
    color: var(--primary-text-color);
  }

  .alert.error ha-icon {
    color: var(--error-color, #db4437);
  }

  .alert.info {
    background-color: color-mix(in srgb, var(--info-color, #039be5) 15%, transparent);
  }

  .alert.info ha-icon {
    color: var(--info-color, #039be5);
  }

  .alert ul {
    margin: 0;
    padding-left: 18px;
  }

  /* ---- setpoint input (temperature / preset / off) */
  .setpoint-input {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
    min-width: 0;
  }

  .setpoint-input select.kind {
    width: 140px;
    flex: 0 0 auto;
  }

  .setpoint-input select.preset {
    flex: 1;
    min-width: 120px;
  }

  .setpoint-input .temperature {
    display: inline-flex;
    align-items: center;
    gap: 2px;
  }

  .setpoint-input .temperature input {
    width: 64px;
    padding: 0 6px;
    text-align: center;
    -moz-appearance: textfield;
  }

  .setpoint-input .temperature input::-webkit-outer-spin-button,
  .setpoint-input .temperature input::-webkit-inner-spin-button {
    -webkit-appearance: none;
    margin: 0;
  }

  .icon-btn.small {
    width: 28px;
    height: 28px;
    --mdc-icon-size: 16px;
  }

  .setpoint-input .unit {
    margin-left: 4px;
  }
`
