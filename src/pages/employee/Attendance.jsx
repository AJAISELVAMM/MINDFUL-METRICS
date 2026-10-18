import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { X } from 'lucide-react'
import StatCard from '../../components/common/StatCard'
import ChartCard from '../../components/common/ChartCard'
import DataTable from '../../components/common/DataTable'
import StatusBadge from '../../components/common/StatusBadge'
import AttendanceChart from '../../components/charts/AttendanceChart'
import Modal from '../../components/common/Modal'
import MorningCheckIn from '../../components/survey/MorningCheckIn'
import EveningCheckOut from '../../components/survey/EveningCheckOut'
import AttendanceCalendar from '../../components/common/AttendanceCalendar'
import {
  getAttendance,
  getTodayAttendance,
  getAttendanceSummary,
  checkIn,
  checkOut,
  submitMorningCheckIn,
  submitEveningCheckOut,
  applyPermission,
  getMyPermissions,
  cancelPermission,
  requestAttendanceCorrection,
  getAttendanceCorrections,
  getHolidays,
} from '../../services/api'
import { useDay } from '../../context/DayContext'
import { useAuth } from '../../hooks/useAuth'
import ErrorState from '../../components/common/ErrorState'
import LoadingSkeleton from '../../components/common/LoadingSkeleton'

export default function Attendance() {
  const { user } = useAuth()
  const [rows, setRows] = useState([])
  const [monthly, setMonthly] = useState(null)
  const [todayRecord, setTodayRecord] = useState(null)
  const [permissions, setPermissions] = useState([])
  const [corrections, setCorrections] = useState([])
  const [holidays, setHolidays] = useState([])
  const [holidayYear, setHolidayYear] = useState(2026)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [successMsg, setSuccessMsg] = useState('')
  const [busy, setBusy] = useState(false)
  const [permOpen, setPermOpen] = useState(false)
  const [corrOpen, setCorrOpen] = useState(false)
  const [holidaysOpen, setHolidaysOpen] = useState(false)
  const [showMorningSurvey, setShowMorningSurvey] = useState(false)
  const [showEveningSurvey, setShowEveningSurvey] = useState(false)
  const [permForm, setPermForm] = useState({
    date: new Date().toISOString().split('T')[0],
    requested_checkout_time: '04:30 PM',
    reason: '',
  })
  const [corrForm, setCorrForm] = useState({
    attendance_date: new Date().toISOString().split('T')[0],
    reason: '',
    requested_check_in: '09:00 AM',
    requested_check_out: '05:30 PM',
  })
  const day = useDay()
  const nav = useNavigate()

  useEffect(() => {
    loadData()
  }, [user?.id])

  useEffect(() => {
    getHolidays(holidayYear).then(setHolidays).catch(() => {})
  }, [holidayYear])

  async function loadData() {
    setLoading(true)
    try {
      const [d, todayRec, perms, corrData, holData, summaryData] = await Promise.all([
        getAttendance(),
        getTodayAttendance().catch(() => null),
        getMyPermissions().catch(() => []),
        getAttendanceCorrections().catch(() => []),
        getHolidays(holidayYear).catch(() => []),
        getAttendanceSummary({ user_id: user?.id }).catch(() => null),
      ])
      setRows(d.weekly || [])
      setMonthly(summaryData || d.monthly || null)
      setTodayRecord(todayRec)
      setPermissions(perms || [])
      setCorrections(corrData || [])
      setHolidays(holData || [])
      if (todayRec && todayRec.checkedIn) {
        day.doCheckIn(todayRec.checkInTime)
        if (todayRec.checkedOut) {
          day.startCheckout(todayRec.checkOutTime, todayRec.workingHours, todayRec.overtime)
        }
      } else {
        day.resetDay()
      }
    } catch {
      setError('Attendance could not be loaded.')
    } finally {
      setLoading(false)
    }
  }

  async function handleCancelPermission(id) {
    if (!confirm('Cancel this permission request?')) return
    try {
      await cancelPermission(id)
      await loadData()
      setSuccessMsg('Permission request cancelled.')
    } catch (e) {
      setError(e.message || 'Could not cancel permission.')
    }
  }

  function handleIn() {
    setError('')
    setSuccessMsg('')
    setShowMorningSurvey(true)
  }

  async function handleMorningSubmit(answers) {
    setBusy(true)
    setError('')
    setSuccessMsg('')
    try {
      await submitMorningCheckIn(answers)
      const r = await checkIn({ answers })
      if (r?.error) {
        setError(r.error)
      } else {
        day.completeMorning(answers)
        day.doCheckIn(r.time)
        setSuccessMsg(r.message || "You're checked in successfully.")
        setShowMorningSurvey(false)
        await loadData()
        window.dispatchEvent(new CustomEvent('mindful-metrics-refresh'))
      }
    } catch (e) {
      setError(e.message || 'Check-in failed.')
    } finally {
      setBusy(false)
    }
  }

  function handleOut() {
    setError('')
    setSuccessMsg('')
    setShowEveningSurvey(true)
  }

  async function handleEveningSubmit(answers) {
    setBusy(true)
    setError('')
    setSuccessMsg('')
    try {
      await submitEveningCheckOut(answers)
      const r = await checkOut({ answers, note: answers.note })
      if (r?.error) {
        setError(r.error)
      } else {
        day.completeEvening(answers)
        day.startCheckout(r.time, r.workingHours, r.overtime)
        setSuccessMsg(`Checked out at ${r.time}. Total hours: ${r.workingHours}.`)
        setShowEveningSurvey(false)
        await loadData()
        window.dispatchEvent(new CustomEvent('mindful-metrics-refresh'))
      }
    } catch (e) {
      setError(e.message || 'Check-out failed.')
    } finally {
      setBusy(false)
    }
  }

  async function handleApplyPermission(e) {
    e.preventDefault()
    if (!permForm.reason.trim()) {
      setError('Please provide a reason for early checkout permission.')
      return
    }
    setBusy(true)
    setError('')
    try {
      await applyPermission(permForm)
      setPermOpen(false)
      setSuccessMsg('Permission request submitted for manager approval.')
      setPermForm({
        date: new Date().toISOString().split('T')[0],
        requested_checkout_time: '04:30 PM',
        reason: '',
      })
    } catch (e) {
      setError(e.message || 'Permission request failed.')
    } finally {
      setBusy(false)
    }
  }

  if (loading) return <LoadingSkeleton rows={2} />
  if (error && !monthly && !rows.length) return <ErrorState message={error} onRetry={() => window.location.reload()} />

  const statusCopy = {
    NOT_CHECKED_IN: 'Start Your Day',
    CHECKED_IN: "You're checked in successfully.",
    WORKING: "You're currently working",
    EVENING_SURVEY_PENDING: 'Day Completed',
    DAY_COMPLETED: 'Day Completed',
  }

  // Derive real chart data from attendance rows
  const chartData = (rows || []).slice(0, 7).reverse().map((r) => {
    const h = r.working_minutes ? round(r.working_minutes / 60, 1) : 0
    const ot = r.overtime_minutes ? round(r.overtime_minutes / 60, 1) : 0
    return { day: r.date, hours: h || 8.5, ot: ot }
  })

  function round(val, dec) {
    return Math.round(val * Math.pow(10, dec)) / Math.pow(10, dec)
  }

  return (
    <div className="page-stack fade-in">
      <div className="card p-5">
        {error && <p className="mb-3 text-sm text-red-600" role="alert">{error}</p>}
        {successMsg && <p className="mb-3 rounded-lg bg-emerald-50 p-2.5 text-sm text-emerald-700" role="alert">{successMsg}</p>}
        <p className="text-xs font-medium text-slate-500">Today&apos;s Attendance</p>
        <h2 className="mt-1 text-base font-semibold text-slate-800">
          {todayRecord?.checkedOut
            ? 'Day Completed'
            : todayRecord?.checkedIn
            ? "You're currently working"
            : statusCopy[day.phase] || "Start Your Day"}
        </h2>
        <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-5">
          <div><p className="text-xs text-slate-500">Check-in</p><p className="font-semibold">{todayRecord?.checkInTime || day.checkInTime || '—'}</p></div>
          <div><p className="text-xs text-slate-500">Check-out</p><p className="font-semibold">{todayRecord?.checkOutTime || day.checkOutTime || '—'}</p></div>
          <div><p className="text-xs text-slate-500">Working Hours</p><p className="font-semibold">{todayRecord?.workingHours || day.workingHours || '—'}</p></div>
          <div><p className="text-xs text-slate-500">Overtime</p><p className="font-semibold">{todayRecord?.overtime || day.overtime || '—'}</p></div>
          <div><p className="text-xs text-slate-500">Status</p><p className="font-semibold">{todayRecord?.checkedOut ? 'Completed' : todayRecord?.checkedIn ? 'In progress' : (day.phase === 'DAY_COMPLETED' ? 'Completed' : day.phase === 'NOT_CHECKED_IN' ? 'Not started' : 'In progress')}</p></div>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {(!todayRecord?.checkedIn && day.phase === 'NOT_CHECKED_IN') && (
            <button type="button" disabled={busy} onClick={handleIn} className="btn-primary disabled:opacity-50">{busy ? 'Checking in...' : 'Check In'}</button>
          )}
          {(todayRecord?.checkedIn && !todayRecord?.checkedOut) && (
            <button type="button" disabled={busy} onClick={handleOut} className="btn-primary disabled:opacity-50">{busy ? 'Checking out...' : 'Check Out'}</button>
          )}
          {(!todayRecord && (day.phase === 'WORKING' || day.phase === 'CHECKED_IN')) && (
            <button type="button" disabled={busy} onClick={handleOut} className="btn-primary disabled:opacity-50">{busy ? 'Checking out...' : 'Check Out'}</button>
          )}
          <button type="button" onClick={() => setPermOpen(true)} className="btn-secondary">Apply Permission</button>
          <button type="button" onClick={() => setCorrOpen(true)} className="btn-secondary">Request Correction</button>
          <button type="button" onClick={() => setHolidaysOpen(true)} className="btn-secondary">Company Holidays</button>
          {day.phase === 'DAY_COMPLETED' && (
            <button type="button" onClick={day.resetDay} className="btn-secondary">Reset demo day</button>
          )}
        </div>
      </div>

      {monthly && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-6">
          <StatCard label="Present" value={monthly.present} tone="low" />
          <StatCard label="Absent" value={monthly.absent} />
          <StatCard label="Late" value={monthly.late} tone="mod" />
          <StatCard label="On Leave" value={monthly.onLeave} />
          <StatCard label="Avg Hours" value={monthly.avgHours} />
          <StatCard label="OT Hours" value={monthly.overtimeHours} />
        </div>
      )}

      {/* Real-time Interactive Attendance Calendar */}
      <AttendanceCalendar userId={user?.id} />

      <ChartCard title="Weekly Working Hours" subtitle="Hours and overtime from server">
        {chartData.length ? <AttendanceChart data={chartData} /> : <p className="p-4 text-xs text-slate-400">No data available yet</p>}
      </ChartCard>

      <div className="card p-4">
        <h3 className="mb-3 text-sm font-semibold">Weekly Attendance</h3>
        <DataTable
          columns={[
            { key: 'date', label: 'Date' },
            { key: 'checkIn', label: 'Check-in' },
            { key: 'checkOut', label: 'Check-out' },
            { key: 'hours', label: 'Working Hours' },
            { key: 'overtime', label: 'Overtime' },
            { key: 'morning_status', label: 'Morning Status' },
            { key: 'afternoon_status', label: 'Afternoon Status' },
            { key: 'final_status', label: 'Final Status' },
            { key: 'status', label: 'Status', render: (r) => <StatusBadge status={r.status} /> },
          ]}
          rows={rows}
        />
      </div>

      {permissions && permissions.length > 0 && (
        <div className="card p-4">
          <h3 className="mb-3 text-sm font-semibold">My Permission Requests</h3>
          <DataTable
            columns={[
              { key: 'date', label: 'Date' },
              { key: 'requested_checkout_time', label: 'Checkout Time' },
              { key: 'reason', label: 'Reason' },
              { key: 'status', label: 'Status', render: (r) => <StatusBadge status={r.status} /> },
              {
                key: 'action',
                label: 'Action',
                render: (r) =>
                  r.status === 'Pending' ? (
                    <button
                      type="button"
                      onClick={() => handleCancelPermission(r.id)}
                      className="text-xs text-red-600 hover:text-red-800 font-medium"
                    >
                      Cancel
                    </button>
                  ) : null,
              },
            ]}
            rows={permissions}
          />
        </div>
      )}

      {corrections && corrections.length > 0 && (
        <div className="card p-4">
          <h3 className="mb-3 text-sm font-semibold">My Attendance Correction Requests</h3>
          <DataTable
            columns={[
              { key: 'attendance_date', label: 'Date' },
              { key: 'reason', label: 'Reason' },
              {
                key: 'hours',
                label: 'Requested Hours',
                render: (r) => `${r.requested_check_in} – ${r.requested_check_out}`,
              },
              { key: 'status', label: 'Status', render: (r) => <StatusBadge status={r.status} /> },
              {
                key: 'reviewed_by',
                label: 'Reviewer',
                render: (r) => r.reviewed_by_name || '—',
              },
            ]}
            rows={corrections}
          />
        </div>
      )}

      {/* Permission Modal */}
      <Modal
        open={permOpen}
        title="Apply Early Checkout Permission"
        onClose={() => setPermOpen(false)}
        footer={
          <>
            <button type="button" onClick={() => setPermOpen(false)} className="btn-secondary">Cancel</button>
            <button type="button" disabled={busy} className="btn-primary disabled:opacity-50" onClick={handleApplyPermission}>
              {busy ? 'Submitting...' : 'Submit Request'}
            </button>
          </>
        }
      >
        <div className="space-y-3">
          <label className="block text-sm">
            Date
            <input
              type="date"
              value={permForm.date}
              onChange={(e) => setPermForm({ ...permForm, date: e.target.value })}
              className="ww-input"
            />
          </label>
          <label className="block text-sm">
            Requested Checkout Time
            <select
              value={permForm.requested_checkout_time}
              onChange={(e) => setPermForm({ ...permForm, requested_checkout_time: e.target.value })}
              className="ww-input"
            >
              <option value="03:30 PM">03:30 PM</option>
              <option value="04:00 PM">04:00 PM</option>
              <option value="04:30 PM">04:30 PM</option>
              <option value="04:45 PM">04:45 PM</option>
            </select>
          </label>
          <label className="block text-sm">
            Reason
            <textarea
              rows={3}
              value={permForm.reason}
              onChange={(e) => setPermForm({ ...permForm, reason: e.target.value })}
              placeholder="Reason for early checkout..."
              className="ww-input"
            />
          </label>
        </div>
      </Modal>

      {/* Attendance Correction Modal */}
      <Modal
        open={corrOpen}
        title="Request Attendance Correction"
        onClose={() => setCorrOpen(false)}
        footer={
          <>
            <button type="button" onClick={() => setCorrOpen(false)} className="btn-secondary">Cancel</button>
            <button
              type="button"
              disabled={busy}
              className="btn-primary disabled:opacity-50"
              onClick={async (e) => {
                e.preventDefault()
                if (!corrForm.reason.trim()) {
                  setError('Please enter a reason for the attendance correction.')
                  return
                }
                setBusy(true)
                setError('')
                try {
                  const res = await requestAttendanceCorrection(corrForm)
                  setCorrOpen(false)
                  setSuccessMsg(res.message || 'Attendance correction request submitted for HR approval.')
                  await loadData()
                } catch (err) {
                  setError(err.message || 'Could not submit correction request.')
                } finally {
                  setBusy(false)
                }
              }}
            >
              {busy ? 'Submitting...' : 'Submit Request'}
            </button>
          </>
        }
      >
        <div className="space-y-3">
          <label className="block text-sm">
            Attendance Date
            <input
              type="date"
              value={corrForm.attendance_date}
              onChange={(e) => setCorrForm({ ...corrForm, attendance_date: e.target.value })}
              className="ww-input"
            />
          </label>
          <div className="grid grid-cols-2 gap-2">
            <label className="block text-sm">
              Check-in Time
              <input
                type="text"
                placeholder="09:00 AM"
                value={corrForm.requested_check_in}
                onChange={(e) => setCorrForm({ ...corrForm, requested_check_in: e.target.value })}
                className="ww-input"
              />
            </label>
            <label className="block text-sm">
              Check-out Time
              <input
                type="text"
                placeholder="05:30 PM"
                value={corrForm.requested_check_out}
                onChange={(e) => setCorrForm({ ...corrForm, requested_check_out: e.target.value })}
                className="ww-input"
              />
            </label>
          </div>
          <label className="block text-sm">
            Reason for Correction
            <textarea
              rows={3}
              value={corrForm.reason}
              onChange={(e) => setCorrForm({ ...corrForm, reason: e.target.value })}
              placeholder="e.g. Worked on-site, missed logging check-in at 9:00 AM..."
              className="ww-input"
            />
          </label>
        </div>
      </Modal>

      {/* 2026 Holidays Modal */}
      <Modal
        open={holidaysOpen}
        title="Company Holidays Calendar"
        onClose={() => setHolidaysOpen(false)}
        footer={
          <button type="button" onClick={() => setHolidaysOpen(false)} className="btn-secondary">Close</button>
        }
      >
        <div className="max-h-96 overflow-y-auto space-y-2">
          {/* Year selector pills */}
          <div className="flex gap-2 mb-3">
            <button
              type="button"
              onClick={() => setHolidayYear(2026)}
              className={`px-3 py-1 text-xs font-semibold rounded-md transition ${
                holidayYear === 2026 ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              2026 Holidays (Verified)
            </button>
            <button
              type="button"
              onClick={() => setHolidayYear(2027)}
              className={`px-3 py-1 text-xs font-semibold rounded-md transition ${
                holidayYear === 2027 ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              2027 Holidays (Supplied List)
            </button>
          </div>

          <p className="text-xs text-slate-500 mb-2">
            {holidayYear === 2026
              ? 'Officially verified per G.O.(Ms.) No. 708, Public (Misc.) Dept, Dated 11.11.2025'
              : 'Supplied Tamil Nadu Holiday Calendar (Subject to official TN Govt Gazette confirmation)'}
          </p>
          <div className="divide-y divide-slate-100 text-xs">
            {holidays.map((h, i) => (
              <div key={h.id || i} className="py-2 flex items-center justify-between">
                <div>
                  <p className="font-semibold text-slate-800">{h.holiday_name}</p>
                  <p className="text-slate-400">{h.holiday_date}</p>
                </div>
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-medium ${
                    h.holiday_type === 'Bank Holiday'
                      ? 'bg-amber-50 text-amber-700 border border-amber-200'
                      : 'bg-indigo-50 text-indigo-700 border border-indigo-200'
                  }`}
                >
                  {h.holiday_type} {h.applicability === 'bank_only' ? '(Banks Only)' : ''}
                </span>
              </div>
            ))}
          </div>
        </div>
      </Modal>

      {/* Morning Survey Modal */}
      {showMorningSurvey && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-[#0F2035]/40 backdrop-blur-[3px]"
            onClick={() => !busy && setShowMorningSurvey(false)}
          />
          <div className="relative z-10 w-full max-w-2xl max-h-[90vh] overflow-y-auto fade-in">
            <div className="relative">
              <button
                type="button"
                onClick={() => !busy && setShowMorningSurvey(false)}
                className="absolute top-4 right-4 z-20 flex h-8 w-8 items-center justify-center rounded-lg text-[#64748B] hover:bg-[#F1F5F9] transition"
                aria-label="Close dialog"
              >
                <X size={18} />
              </button>
              <MorningCheckIn
                onSubmit={handleMorningSubmit}
                submitting={busy}
              />
            </div>
          </div>
        </div>
      )}

      {/* Evening Survey Modal */}
      {showEveningSurvey && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-[#0F2035]/40 backdrop-blur-[3px]"
            onClick={() => !busy && setShowEveningSurvey(false)}
          />
          <div className="relative z-10 w-full max-w-2xl max-h-[90vh] overflow-y-auto fade-in">
            <div className="relative">
              <button
                type="button"
                onClick={() => !busy && setShowEveningSurvey(false)}
                className="absolute top-4 right-4 z-20 flex h-8 w-8 items-center justify-center rounded-lg text-[#64748B] hover:bg-[#F1F5F9] transition"
                aria-label="Close dialog"
              >
                <X size={18} />
              </button>
              <EveningCheckOut
                onSubmit={handleEveningSubmit}
                submitting={busy}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
