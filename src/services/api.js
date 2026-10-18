function getApiBaseUrl() {
  const envUrl = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname
    const isLocalhost = hostname === 'localhost' || hostname === '127.0.0.1'
    if (isLocalhost) {
      return 'http://localhost:8000'
    }
    if (hostname.includes('trycloudflare.com')) {
      return ''
    }
  }
  return envUrl || 'http://localhost:8000'
}

function token() {
  try {
    const raw = localStorage.getItem('mm_session') || sessionStorage.getItem('mm_session')
    return raw ? JSON.parse(raw).token : null
  } catch {
    return null
  }
}

const apiCache = new Map()
const inFlight = new Map()

export function clearApiCache() {
  apiCache.clear()
  inFlight.clear()
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('mindful-metrics-refresh'))
  }
}

export async function getBackendStatus() {
  try {
    const baseUrl = getApiBaseUrl()
    const signal = typeof AbortSignal !== 'undefined' && AbortSignal.timeout ? AbortSignal.timeout(8000) : undefined
    const res = await fetch(`${baseUrl}/api/health`, { method: 'GET', signal })
    if (!res.ok) return { ok: false, status: 'Backend Unavailable' }
    const data = await res.json()
    return { ok: true, status: 'Backend Connected', data }
  } catch {
    return { ok: false, status: 'Backend Unavailable' }
  }
}

async function executeFetch(path, options, cacheKey, isGet, now) {
  try {
    const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) }
    const t = token()
    if (t) headers.Authorization = `Bearer ${t}`
    const baseUrl = getApiBaseUrl()
    
    // 15 second request timeout to avoid hanging connections
    const signal = options.signal || (typeof AbortSignal !== 'undefined' && AbortSignal.timeout ? AbortSignal.timeout(15000) : undefined)
    const res = await fetch(`${baseUrl}/api${path}`, { ...options, headers, signal })

    if (res.status === 401) {
      clearApiCache()
      localStorage.removeItem('mm_session')
      sessionStorage.removeItem('mm_session')
      const err = new Error('unauthorized')
      err.status = 401
      if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
        window.location.assign('/login')
      }
      throw err
    }

    if (!res.ok) {
      const msg = await res.text()
      try {
        const parsed = JSON.parse(msg)
        throw new Error(parsed.detail || parsed.message || msg)
      } catch (parseErr) {
        if (parseErr.message && !parseErr.message.includes('JSON')) throw parseErr
        throw new Error(msg || 'Request failed')
      }
    }

    const data = await res.json()
    if (isGet) {
      apiCache.set(cacheKey, { data, timestamp: now })
    }
    return data
  } finally {
    if (isGet) {
      inFlight.delete(cacheKey)
    }
  }
}

function getCacheKey(path) {
  const t = token()
  const tokenHash = t ? t.slice(-16) : 'anonymous'
  return `${tokenHash}:${path}`
}

async function request(path, options = {}) {
  const method = (options.method || 'GET').toUpperCase()
  const isGet = method === 'GET'

  if (!isGet) {
    clearApiCache()
  }

  const cacheKey = getCacheKey(path)
  const now = Date.now()

  // 1. Check memory cache for fresh GET responses
  if (isGet && !options.skipCache) {
    const cached = apiCache.get(cacheKey)
    const ttl = (options.ttlSeconds || 20) * 1000
    if (cached && now - cached.timestamp < ttl) {
      return cached.data
    }
  }

  // 2. Reuse in-flight GET requests to eliminate duplicate simultaneous calls
  if (isGet && !options.skipCache && inFlight.has(cacheKey)) {
    return inFlight.get(cacheKey)
  }

  const promise = executeFetch(path, options, cacheKey, isGet, now)
  if (isGet && !options.skipCache) {
    inFlight.set(cacheKey, promise)
  }

  return promise
}

// Auth
export async function loginRequest(email, password) {
  clearApiCache()
  return request('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) })
}

export async function logoutRequest() {
  clearApiCache()
  try {
    return await request('/auth/logout', { method: 'POST' })
  } catch {
    return { ok: true }
  }
}

export async function getMe() {
  return request('/auth/me')
}

export async function getUserProfile() {
  return request('/user/profile')
}

export async function updateUserProfile(payload) {
  return request('/user/profile', { method: 'PUT', body: JSON.stringify(payload) })
}

export async function uploadAvatar(avatar) {
  return request('/user/avatar', { method: 'POST', body: JSON.stringify({ avatar }) })
}

export async function removeAvatar() {
  return request('/user/avatar', { method: 'DELETE' })
}

export async function changePassword(currentPassword, newPassword) {
  return request('/user/change-password', {
    method: 'POST',
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  })
}

// Attendance
export async function getEmployeeDashboard(options = {}) {
  return request('/employee/dashboard', options)
}

export async function getAttendance() {
  return request('/attendance/weekly')
}

export async function getTodayAttendance() {
  return request('/attendance/today')
}

export async function checkIn(payload = null) {
  clearApiCache()
  return request('/attendance/check-in', {
    method: 'POST',
    body: JSON.stringify(payload || {}),
  })
}

export async function checkOut(payload = null) {
  clearApiCache()
  return request('/attendance/check-out', {
    method: 'POST',
    body: JSON.stringify(payload || {}),
  })
}

export async function getTeamAttendance() {
  return request('/attendance/team')
}

export async function getHRAttendance(params = {}) {
  const query = new URLSearchParams()
  if (params.department) query.set('department', params.department)
  if (params.status) query.set('status', params.status)
  const qs = query.toString()
  return request(`/attendance/all${qs ? `?${qs}` : ''}`)
}

// Holidays
export async function getHolidays(year = 2026) {
  return request(`/holidays?year=${year}`)
}

// Attendance Corrections
export async function requestAttendanceCorrection(payload) {
  clearApiCache()
  return request('/attendance/correction/request', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function getAttendanceCorrections(status) {
  const query = status && status !== 'All' ? `?status=${status}` : ''
  return request(`/attendance/correction/requests${query}`)
}

export async function approveAttendanceCorrection(correctionId) {
  clearApiCache()
  return request(`/attendance/correction/${correctionId}/approve`, {
    method: 'POST',
  })
}

export async function rejectAttendanceCorrection(correctionId, rejectionReason) {
  clearApiCache()
  return request(`/attendance/correction/${correctionId}/reject`, {
    method: 'POST',
    body: JSON.stringify({ rejection_reason: rejectionReason }),
  })
}

export async function getAttendanceSummary(params = {}) {
  const query = new URLSearchParams()
  if (params.date) query.set('date', params.date)
  if (params.year) query.set('year', params.year)
  if (params.month) query.set('month', params.month)
  if (params.department) query.set('department', params.department)
  if (params.user_id) query.set('user_id', params.user_id)
  const qs = query.toString()
  return request(`/attendance/summary${qs ? `?${qs}` : ''}`)
}

export async function getAttendanceCalendar(params = {}) {
  const query = new URLSearchParams()
  if (params.year) query.set('year', params.year)
  if (params.month) query.set('month', params.month)
  if (params.user_id) query.set('user_id', params.user_id)
  const qs = query.toString()
  return request(`/attendance/calendar${qs ? `?${qs}` : ''}`)
}

export async function getSundaysList(startYear = 2026, endYear = 2027) {
  return request(`/attendance/sundays?start_year=${startYear}&end_year=${endYear}`)
}

export async function seed2027Holidays() {
  clearApiCache()
  return request('/attendance/holidays/seed-2027', { method: 'POST' })
}

export async function recoverAttendance(maxDays = 14) {
  clearApiCache()
  return request(`/attendance/recover?max_days=${maxDays}`, { method: 'POST' })
}

export async function triggerDailyFinalize(date, force = false) {
  clearApiCache()
  return request('/attendance/finalize-daily', {
    method: 'POST',
    body: JSON.stringify({ ...(date ? { date } : {}), force }),
  })
}

// Survey
export async function getSurveyQuestions() {
  return request('/survey/questions')
}

export async function getSurveyToday() {
  return request('/survey/today')
}

export async function submitDailySurvey(payload, survey_type = 'daily') {
  clearApiCache()
  return request(`/survey/daily?survey_type=${survey_type}`, { method: 'POST', body: JSON.stringify(payload) })
}

export async function submitMorningCheckIn(payload) {
  clearApiCache()
  return request('/survey/daily?survey_type=morning', { method: 'POST', body: JSON.stringify({ answers: payload }) })
}

export async function submitEveningCheckOut(payload) {
  clearApiCache()
  return request('/survey/daily?survey_type=evening', { method: 'POST', body: JSON.stringify({ answers: payload, note: payload.note || '' }) })
}

export async function submitPulseSurvey(workload) {
  clearApiCache()
  return request('/survey/pulse', { method: 'POST', body: JSON.stringify({ workload }) })
}

// Leave
export async function getLeaveData() {
  return request('/leave/my')
}

export async function applyLeave(form) {
  return request('/leave', { method: 'POST', body: JSON.stringify(form) })
}

export async function getTeamLeave() {
  return request('/leave/team')
}

export async function getHRLeaves(filters = {}) {
  const query = new URLSearchParams()
  if (filters.employee) query.set('employee', filters.employee)
  if (filters.department) query.set('department', filters.department)
  if (filters.role) query.set('role', filters.role)
  if (filters.leave_type) query.set('leave_type', filters.leave_type)
  if (filters.status) query.set('status', filters.status)
  const qs = query.toString()
  return request(`/leave/all${qs ? `?${qs}` : ''}`)
}

export async function updateLeaveRequest(id, status) {
  return request(`/manager/leave-requests/${encodeURIComponent(id)}`, { method: 'PATCH', body: JSON.stringify({ status }) })
}

export async function cancelLeave(id) {
  return request(`/leave/${encodeURIComponent(id)}`, { method: 'DELETE' })
}

// Permission
export async function getMyPermissions() {
  return request('/permission/my')
}

export async function applyPermission(form) {
  return request('/permission', { method: 'POST', body: JSON.stringify(form) })
}

export async function cancelPermission(id) {
  return request(`/permission/${encodeURIComponent(id)}`, { method: 'DELETE' })
}

export async function getTeamPermissions() {
  return request('/permission/team')
}

export async function getHRPermissions() {
  return request('/permission/all')
}

export async function updatePermission(id, status) {
  return request(`/permission/${encodeURIComponent(id)}/${status.toLowerCase()}`, { method: 'PATCH' })
}

// Tasks / Work
export async function getWorkData() {
  return request('/tasks/my')
}

export async function createTask(task) {
  clearApiCache()
  return request('/tasks', { method: 'POST', body: JSON.stringify(task) })
}

export async function updateTaskStatus(id, status) {
  clearApiCache()
  return request(`/tasks/${encodeURIComponent(id)}`, { method: 'PATCH', body: JSON.stringify({ status }) })
}

export async function updateTaskDetails(id, payload) {
  clearApiCache()
  return request(`/tasks/${encodeURIComponent(id)}`, { method: 'PUT', body: JSON.stringify(payload) })
}

export async function getTeamWorkload() {
  return request('/tasks/team')
}

export async function getHRTasks() {
  return request('/tasks/all')
}

// Task Unblock Request & Verification APIs
export async function submitTaskUnblockRequest(taskId, payload) {
  clearApiCache()
  return request(`/tasks/${encodeURIComponent(taskId)}/unblock-request`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function replyTaskUnblockClarification(requestId, response) {
  clearApiCache()
  return request(`/tasks/unblock-requests/${encodeURIComponent(requestId)}/reply`, {
    method: 'POST',
    body: JSON.stringify({ response }),
  })
}

export async function getHRUnblockRequests() {
  return request('/hr/tasks/unblock-requests')
}

export async function approveTaskUnblock(requestId, reason = 'Approved by HR') {
  clearApiCache()
  return request(`/hr/tasks/unblock-requests/${encodeURIComponent(requestId)}/approve`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  })
}

export async function clarifyTaskUnblock(requestId, message) {
  clearApiCache()
  return request(`/hr/tasks/unblock-requests/${encodeURIComponent(requestId)}/clarify`, {
    method: 'POST',
    body: JSON.stringify({ message }),
  })
}

export async function rejectTaskUnblock(requestId, reason) {
  clearApiCache()
  return request(`/hr/tasks/unblock-requests/${encodeURIComponent(requestId)}/reject`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  })
}

export async function getHRVerificationQueue() {
  return request('/hr/tasks/verification-queue')
}

export async function verifyTask(taskId, notes = '') {
  clearApiCache()
  return request(`/hr/tasks/${encodeURIComponent(taskId)}/verify`, {
    method: 'POST',
    body: JSON.stringify({ notes }),
  })
}

export async function requestTaskChanges(taskId, notes) {
  clearApiCache()
  return request(`/hr/tasks/${encodeURIComponent(taskId)}/request-changes`, {
    method: 'POST',
    body: JSON.stringify({ notes }),
  })
}

// Burnout & Analytics
export async function getBurnoutAnalysis() {
  return request('/burnout/current')
}

export async function getBurnoutTrends() {
  return request('/burnout/trend')
}

export async function getRecommendations() {
  return request('/burnout/recommendations')
}

// Manager
export async function getTeamDashboard() {
  return request('/manager/dashboard')
}

export async function getTeamMembers() {
  return request('/manager/team')
}

export async function getManagerTrends() {
  return request('/manager/trends')
}

// HR
export async function getHRDashboard() {
  return request('/hr/dashboard')
}

export async function getHRTrends() {
  return request('/hr/trends')
}

export async function getEmployees() {
  return request('/hr/employees')
}

export async function getDepartments() {
  return request('/hr/departments')
}

export async function getModelPerformance() {
  return request('/hr/model-performance')
}

export async function getInterventions() {
  return request('/hr/interventions')
}

export async function createIntervention(data) {
  return request('/hr/interventions', { method: 'POST', body: JSON.stringify(data) })
}

export async function updateIntervention(id, data) {
  return request(`/hr/interventions/${encodeURIComponent(id)}`, { method: 'PATCH', body: JSON.stringify(data) })
}

export async function getInterventionCandidates() {
  return request('/hr/interventions/candidates')
}

// Settings
export async function getCompanySettings() {
  return request('/settings/company')
}

export async function updateCompanySettings(settings) {
  return request('/settings/company', { method: 'PUT', body: JSON.stringify(settings) })
}

// Notifications
export async function getNotifications(includeArchived = false) {
  return request(`/notifications${includeArchived ? '?include_archived=true' : ''}`, { skipCache: true })
}

export async function getUnreadNotificationCount() {
  return request('/notifications/unread-count', { skipCache: true })
}

export async function markNotificationRead(id) {
  return request(`/notifications/${id}/read`, { method: 'POST', skipCache: true })
}

export async function markAllNotificationsRead() {
  return request('/notifications/mark-all-read', { method: 'POST', skipCache: true })
}

export async function archiveNotification(id) {
  return request(`/notifications/${id}/archive`, { method: 'POST', skipCache: true })
}

// AI Chat
export async function sendAssistantMessage(role, text, context = {}) {
  const payload = { text, role, ...context }
  const data = await request('/ai/chat', { method: 'POST', body: JSON.stringify(payload) })
  if (typeof data === 'string') return data
  return data.reply || data.message || String(data)
}

// Full Details
export async function getUserFullDetails(userId) {
  return request(`/users/${encodeURIComponent(userId)}/details`, { skipCache: true })
}


