import { localize } from '../../localize/localize'
import { type Prog } from '../../panel/api/prog/dto/prog'

export const dayToStr = (day: number, language: string): string => {
  switch (day) {
    case 0: return localize('dayOfWeek.monday', language)
    case 1: return localize('dayOfWeek.tuesday', language)
    case 2: return localize('dayOfWeek.wednesday', language)
    case 3: return localize('dayOfWeek.thursday', language)
    case 4: return localize('dayOfWeek.friday', language)
    case 5: return localize('dayOfWeek.saturday', language)
    case 6: return localize('dayOfWeek.sunday', language)
    default: return localize('error', language)
  }
}

export const orderToStr = (order: number, language: string): string => {
  switch (order) {
    case 0: return localize('state.comfort', language)
    case 1: return localize('state.eco', language)
    case 2: return localize('state.frostFree', language)
    default: return localize('error', language)
  }
}

export const progToUTC = (prog: Prog): Prog => {
  // Convert time to UTC
  // Change day if necessary
  const result = ConvertDayAndHourUTC(prog.day, prog.hour)
  return { ...prog, ...result }
}

export const progFromUTC = (prog: Prog): Prog => {
  // Convert time to local time
  // Change day if necessary
  const result = ConvertDayAndHourUTC(prog.day, prog.hour, true)
  return { ...prog, ...result }
}

/**
 * Switch hour and day from/to UTC
 * @param day prog day
 * @param hour prog hour
 * @param fromUTC true => Local time > UTC time<br>
 *   false => UTC time > Local time
 */
const ConvertDayAndHourUTC = (day: number, hour: string, fromUTC = false): { day: number, hour: string } => {
  const timeZoneOffset = new Date().getTimezoneOffset()
  let dayOffset = 0
  const [hours, minutes] = hour.split(':').map(Number)

  let finalHour = hours * 60
  if (fromUTC) finalHour = (finalHour - timeZoneOffset) / 60
  else finalHour = (finalHour + timeZoneOffset) / 60

  if (finalHour < 0) {
    dayOffset = -1
    finalHour = 24 + finalHour
  }
  if (finalHour >= 24) {
    dayOffset = 1
    finalHour = 24 - finalHour
  }

  let dayUTC = day + dayOffset
  if (dayUTC < 0) {
    dayUTC = 6
  }
  if (dayUTC > 6) {
    dayUTC = 0
  }

  return {
    day: dayUTC,
    hour: `${finalHour.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`
  }
}
