import { createContext, useCallback, useContext, useMemo, useState } from 'react'

const DayContext = createContext(null)

function getCurrentUserKey() {
  try {
    const raw = localStorage.getItem('mm_session') || sessionStorage.getItem('mm_session')
    if (raw) {
      const parsed = JSON.parse(raw)
      if (parsed?.id) return `ww_day_state_${parsed.id}`
    }
  } catch {
    /* ignore */
  }
  return 'ww_day_state'
}

function load() {
  try {
    const key = getCurrentUserKey()
    const raw = localStorage.getItem(key)
    if (raw) return JSON.parse(raw)
  } catch {
    /* ignore */
  }
  return {
    phase: 'NOT_CHECKED_IN',
    checkInTime: null,
    checkOutTime: null,
    morning: null,
    evening: null,
    workingHours: null,
    overtime: null,
  }
}

export function DayProvider({ children }) {
  const [state, setState] = useState(load)

  const persist = useCallback((next) => {
    setState(next)
    const key = getCurrentUserKey()
    localStorage.setItem(key, JSON.stringify(next))
  }, [])

  const doCheckIn = useCallback((time) => {
    persist({ ...state, phase: 'CHECKED_IN', checkInTime: time })
  }, [persist, state])

  const completeMorning = useCallback((answers) => {
    persist({ ...state, phase: 'WORKING', morning: answers })
  }, [persist, state])

  const startCheckout = useCallback((time, workingHours = null, overtime = null) => {
    persist({ ...state, phase: 'EVENING_SURVEY_PENDING', checkOutTime: time, workingHours, overtime })
  }, [persist, state])

  const completeEvening = useCallback((answers) => {
    persist({ ...state, phase: 'DAY_COMPLETED', evening: answers })
  }, [persist, state])

  const resetDay = useCallback(() => {
    const empty = {
      phase: 'NOT_CHECKED_IN',
      checkInTime: null,
      checkOutTime: null,
      morning: null,
      evening: null,
      workingHours: null,
      overtime: null,
    }
    persist(empty)
  }, [persist])

  const value = useMemo(
    () => ({ ...state, doCheckIn, completeMorning, startCheckout, completeEvening, resetDay }),
    [state, doCheckIn, completeMorning, startCheckout, completeEvening, resetDay],
  )

  return <DayContext.Provider value={value}>{children}</DayContext.Provider>
}

export function useDay() {
  const ctx = useContext(DayContext)
  if (!ctx) throw new Error('useDay')
  return ctx
}
