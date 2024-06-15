import * as en from './languages/en.json'
import * as fr from './languages/fr.json'

import IntlMessageFormat from 'intl-messageformat'

const LANGUAGES: any = {
  en,
  fr
}

export function localize (string: string, language: string, ...args: any[]): string {
  const lang = language.replace(/['"]+/g, '')

  let translated: string

  try {
    translated = string.split('.').reduce((o, i) => o[i], LANGUAGES[lang])
  } catch (e) {
    translated = string.split('.').reduce((o, i) => o[i], LANGUAGES.en)
  }

  if (translated === undefined) translated = string.split('.').reduce((o, i) => o[i], LANGUAGES.en)

  if (args.length === 0) return translated

    type arg = Record<string, any>
    const argObject: arg = {}
    for (let i = 0; i < args.length; i += 2) {
      let key = args[i]
      key = key.replace(/^{([^}]+)?}$/, '$1')
      argObject[key] = args[i + 1]
    }

    try {
      const message = new IntlMessageFormat(translated, language)
      return message.format(argObject) as string
    } catch (err) {
      return `Translation ${String(err)}`
    }
}
