import { useState, useEffect } from 'react'
import { useAuth } from '../../hooks/useAuth'
import { getMe, updateUserProfile } from '../../services/api'

export default function Profile() {
  const { user, updateSession } = useAuth()
  const [profile, setProfile] = useState(user || {})
  const [savedMsg, setSavedMsg] = useState('')
  const [form, setForm] = useState(() => {
    try {
      return (
        JSON.parse(localStorage.getItem('mm_profile') || 'null') || {
          phone: user?.phone || '+91 98765 43210',
          location: 'Bengaluru, India',
        }
      )
    } catch {
      return { phone: user?.phone || '+91 98765 43210', location: 'Bengaluru, India' }
    }
  })

  useEffect(() => {
    getMe()
      .then((data) => {
        if (data) {
          setProfile(data)
          if (data.phone) {
            setForm((f) => ({ ...f, phone: data.phone }))
          }
        }
      })
      .catch(() => {})
  }, [])

  async function saveProfile() {
    try {
      localStorage.setItem('mm_profile', JSON.stringify(form))
      await updateUserProfile({ phone: form.phone })
      if (updateSession) updateSession({ phone: form.phone })
      setSavedMsg('Profile changes saved successfully.')
    } catch {
      setSavedMsg('Profile changes saved locally.')
    }
    setTimeout(() => setSavedMsg(''), 3000)
  }

  const name = profile.name || user?.name || 'User'
  const initials = name
    .split(' ')
    .map((p) => p[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()

  return (
    <div className="fade-in grid gap-4 lg:grid-cols-[280px_1fr]">
      <div className="card p-6 text-center">
        <div className="mx-auto mb-3 flex h-16 w-16 items-center justify-center rounded-full bg-[#10243B] text-lg font-semibold text-white overflow-hidden">
          {user?.avatar || profile.avatar ? (
            <img src={user?.avatar || profile.avatar} alt={name} className="h-full w-full object-cover" />
          ) : (
            initials
          )}
        </div>
        <p className="font-semibold text-[#172B4D]">{name}</p>
        <p className="text-[12px] text-[#6B7C93]">
          {profile.employeeId || user?.employeeId || '—'} · {profile.department || user?.department || '—'}
        </p>
        <p className="mt-2 text-[12px] font-semibold capitalize text-[#1E6BFF]">{profile.role || user?.role || 'Employee'}</p>
      </div>
      <div className="card p-6">
        <h3 className="mb-4 text-[14px] font-semibold">Profile details</h3>
        <dl className="grid grid-cols-2 gap-4 text-[13px]">
          <div>
            <dt className="text-[11px] text-[#6B7C93]">Email</dt>
            <dd className="font-medium text-slate-800">{profile.email || user?.email}</dd>
          </div>
          <div>
            <dt className="text-[11px] text-[#6B7C93]">Department</dt>
            <dd className="font-medium text-slate-800">{profile.department || user?.department || '—'}</dd>
          </div>
          <div>
            <dt className="text-[11px] text-[#6B7C93]">Reporting Manager</dt>
            <dd className="font-medium text-slate-800">{profile.manager || user?.manager || '—'}</dd>
          </div>
          <div>
            <dt className="text-[11px] text-[#6B7C93]">Employee ID</dt>
            <dd className="font-medium text-slate-800">{profile.employeeId || user?.employeeId || '—'}</dd>
          </div>
        </dl>
        <label className="mt-4 block text-[12px] font-medium text-[#6B7C93]">
          Phone
          <input
            value={form.phone}
            onChange={(e) => setForm({ ...form, phone: e.target.value })}
            className="ww-input"
          />
        </label>
        <label className="mt-3 block text-[12px] font-medium text-[#6B7C93]">
          Location
          <input
            value={form.location}
            onChange={(e) => setForm({ ...form, location: e.target.value })}
            className="ww-input"
          />
        </label>
        <div className="mt-4 flex items-center gap-3">
          <button type="button" onClick={saveProfile} className="btn-primary">
            Save changes
          </button>
          {savedMsg && <span className="text-xs font-medium text-emerald-600">{savedMsg}</span>}
        </div>
      </div>
    </div>
  )
}
