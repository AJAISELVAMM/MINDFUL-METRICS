import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { loginRequest, logoutRequest, getMe } from '../services/api'

export const AuthContext = createContext(null)

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    try {
      const raw = localStorage.getItem('mm_session') || sessionStorage.getItem('mm_session')
      if (raw) {
        const s = JSON.parse(raw)
        if (s.token && s.role) {
          setUser(s)
          getMe()
            .then((meData) => {
              if (meData && meData.email) {
                setUser((curr) => {
                  if (!curr) return null
                  const updated = {
                    ...curr,
                    id: meData.id || curr.id,
                    name: meData.name || curr.name,
                    phone: meData.phone || curr.phone,
                    department: meData.department || curr.department,
                    employeeId: meData.employeeId || curr.employeeId,
                    avatar: meData.avatar !== undefined ? meData.avatar : curr.avatar,
                  }
                  try {
                    if (localStorage.getItem('mm_session')) {
                      localStorage.setItem('mm_session', JSON.stringify(updated))
                    } else if (sessionStorage.getItem('mm_session')) {
                      sessionStorage.setItem('mm_session', JSON.stringify(updated))
                    }
                  } catch {
                    /* ignore */
                  }
                  return updated
                })
              }
            })
            .catch(() => {})
        }
      }
    } catch {
      /* ignore */
    }
    setReady(true)
  }, [])

  const login = useCallback(async (email, password, remember = true) => {
    try {
      const data = await loginRequest(email, password)
      const session = {
        id: data.user.id,
        email: data.user.email,
        role: data.user.role,
        name: data.user.name,
        department: data.user.department,
        employeeId: data.user.employeeId,
        phone: data.user.phone,
        avatar: data.user.avatar,
        token: data.token,
      }
      localStorage.removeItem('mm_session')
      sessionStorage.removeItem('mm_session')
      localStorage.removeItem('ww_day_state')
      localStorage.removeItem('mm_profile')
      sessionStorage.removeItem('mm_last_page')
      const storage = remember ? localStorage : sessionStorage
      storage.setItem('mm_session', JSON.stringify(session))
      setUser(session)
      return { ok: true, session }
    } catch (err) {
      return { ok: false, error: err.message || 'Invalid credentials or API unavailable.' }
    }
  }, [])

  const updateSession = useCallback((updates) => {
    setUser((prev) => {
      if (!prev) return null
      const next = { ...prev, ...updates }
      try {
        if (localStorage.getItem('mm_session')) {
          localStorage.setItem('mm_session', JSON.stringify(next))
        } else if (sessionStorage.getItem('mm_session')) {
          sessionStorage.setItem('mm_session', JSON.stringify(next))
        }
      } catch {
        /* ignore */
      }
      return next
    })
  }, [])

  const logout = useCallback(() => {
    logoutRequest().catch(() => {})
    localStorage.removeItem('mm_session')
    sessionStorage.removeItem('mm_session')
    localStorage.removeItem('ww_day_state')
    localStorage.removeItem('mm_profile')
    sessionStorage.removeItem('mm_last_page')
    setUser(null)
  }, [])

  const value = useMemo(
    () => ({ user, ready, login, logout, updateSession }),
    [user, ready, login, logout, updateSession],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
