import { useEffect, useState } from 'react'
import { Clock, CheckCircle2, AlertCircle, X } from 'lucide-react'
import { getTodayAttendance, checkIn, checkOut, submitMorningCheckIn, submitEveningCheckOut } from '../../services/api'
import { useDay } from '../../context/DayContext'
import RiskBadge from './RiskBadge'
import MorningCheckIn from '../survey/MorningCheckIn'
import EveningCheckOut from '../survey/EveningCheckOut'

export default function TodayAttendanceCard({ onAttendanceChange, roleLabel, myBurnout, onOpenDetails }) {
  const [att, setAtt] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [busyAction, setBusyAction] = useState(null)
  const [msg, setMsg] = useState('')
  const [err, setErr] = useState('')
  const [showMorningSurvey, setShowMorningSurvey] = useState(false)
  const [showEveningSurvey, setShowEveningSurvey] = useState(false)
  const day = useDay()

  useEffect(() => {
    loadAttendance()
  }, [])

  async function loadAttendance() {
    setLoading(true)
    try {
      const data = await getTodayAttendance()
      setAtt(data)
      if (data?.checkedIn && day?.doCheckIn && !day.checkInTime) {
        day.doCheckIn(data.checkInTime)
      }
      if (data?.checkedOut && day?.startCheckout && !day.checkOutTime) {
        day.startCheckout(data.checkOutTime, data.workingHours, data.overtime)
      }
      if (!data?.checkedIn && day?.resetDay && (day.checkInTime || day.phase !== 'NOT_CHECKED_IN')) {
        day.resetDay()
      }
    } catch {
      // If error loading, fallback to empty state
    } finally {
      setLoading(false)
    }
  }

  function handleCheckIn() {
    if (busy || loading) return
    if (att?.checkedIn) {
      setErr("You're already checked in today.")
      return
    }
    setErr('')
    setMsg('')
    setShowMorningSurvey(true)
  }

  async function handleMorningSubmit(answers) {
    setBusy(true)
    setBusyAction('in')
    setErr('')
    setMsg('')
    try {
      await submitMorningCheckIn(answers)
      const res = await checkIn({ answers })
      if (res?.error) {
        setErr(res.error)
      } else {
        setMsg(res.message || "You're checked in successfully.")
        if (day?.completeMorning) day.completeMorning(answers)
        if (day?.doCheckIn) day.doCheckIn(res.time)
        setShowMorningSurvey(false)
        await loadAttendance()
        onAttendanceChange?.()
        window.dispatchEvent(new CustomEvent('mindful-metrics-refresh'))
      }
    } catch (e) {
      setErr(e.message || 'Check-in failed. Please try again.')
    } finally {
      setBusy(false)
      setBusyAction(null)
    }
  }

  function handleCheckOut() {
    if (busy || loading) return
    if (!att?.checkedIn) {
      setErr('Please check in first.')
      return
    }
    if (att?.checkedOut) {
      setErr("Today's attendance is already completed.")
      return
    }
    setErr('')
    setMsg('')
    setShowEveningSurvey(true)
  }

  async function handleEveningSubmit(answers) {
    setBusy(true)
    setBusyAction('out')
    setErr('')
    setMsg('')
    try {
      await submitEveningCheckOut(answers)
      const res = await checkOut({ answers, note: answers.note })
      if (res?.error) {
        setErr(res.error)
      } else {
        setMsg(`Checked out at ${res.time}. Total hours: ${res.workingHours}.`)
        if (day?.completeEvening) day.completeEvening(answers)
        if (day?.startCheckout) {
          day.startCheckout(res.time, res.workingHours, res.overtime)
        }
        setShowEveningSurvey(false)
        await loadAttendance()
        onAttendanceChange?.()
        window.dispatchEvent(new CustomEvent('mindful-metrics-refresh'))
      }
    } catch (e) {
      setErr(e.message || 'Check-out failed. Please try again.')
    } finally {
      setBusy(false)
      setBusyAction(null)
    }
  }

  // Format single-digit leading hour (e.g., '08h 06m' -> '8h 06m', '00h 00m' -> '0h 00m')
  function formatDuration(str) {
    if (!str || str === '—') return str
    return str.replace(/^0(\d)h/, '$1h')
  }

  // Format status badge text
  const isCheckedIn = Boolean(att?.checkedIn)
  const isCheckedOut = Boolean(att?.checkedOut)

  let statusText = 'Not Checked In'
  let statusTone = 'slate'

  if (isCheckedOut) {
    if (att?.final_status === 'FULL_DAY_PRESENT' || att?.final_status === 'PRESENT_WITH_APPROVED_PERMISSION' || att?.status === 'Completed') {
      statusText = 'Present'
      statusTone = 'green'
    } else if (att?.final_status?.includes('HALF') || att?.final_status?.includes('ABSENT')) {
      statusText = 'Half-Day Absent'
      statusTone = 'amber'
    } else if (att?.final_status === 'UNAUTHORIZED_EARLY_CHECKOUT') {
      statusText = 'Early Checkout / Absent'
      statusTone = 'amber'
    } else if (att?.final_status?.includes('LEAVE')) {
      statusText = 'On Leave'
      statusTone = 'amber'
    } else if (att?.final_status === 'ATTENDANCE_EXCEPTION') {
      statusText = 'Attendance Exception'
      statusTone = 'amber'
    } else {
      statusText = att?.status || 'Present'
      statusTone = 'green'
    }
  } else if (isCheckedIn) {
    if (att?.morning_status === 'PRESENT') {
      statusText = 'Present'
      statusTone = 'green'
    } else if (att?.morning_status?.includes('HALF') || att?.morning_status?.includes('ABSENT')) {
      statusText = 'Morning Half-Day Absent'
      statusTone = 'amber'
    } else if (att?.morning_status?.includes('LEAVE')) {
      statusText = 'Morning Leave'
      statusTone = 'amber'
    } else {
      statusText = att?.morning_status || 'Present'
      statusTone = 'blue'
    }
  }

  const workingHoursDisplay = isCheckedOut
    ? formatDuration(att?.workingHours) || '—'
    : isCheckedIn
    ? 'calculating...'
    : '—'

  const overtimeDisplay = isCheckedOut
    ? formatDuration(att?.overtime) || '0h 00m'
    : '—'

  const burnoutScore = myBurnout?.burnout_score ?? att?.burnout_score
  const topRec = myBurnout?.recommendations?.[0] || att?.burnout_rec
  const showBurnoutMetric = (roleLabel === 'Manager' || myBurnout) && burnoutScore !== null && burnoutScore !== undefined

  return (
    <div className="card p-5 bg-white border-[#E2EAF2] shadow-sm transition-all">
      {/* Top row: Title & Action buttons */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#EFF6FF] text-[#1E6BFF] shrink-0">
            <Clock size={18} strokeWidth={2} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-[15px] font-bold text-[#0D192B] tracking-tight">
                Today&apos;s Attendance
              </h3>
              {roleLabel && (
                <span className="rounded-full bg-[#F1F5F9] px-2 py-0.5 text-[10px] font-semibold text-[#64748B]">
                  {roleLabel}
                </span>
              )}
            </div>
            <p className="text-[11px] text-[#64748B] mt-0.5 font-medium">
              Official hours: 09:00 AM – 05:30 PM
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2.5">
          {!isCheckedIn && (
            <button
              type="button"
              disabled={busy || loading}
              onClick={handleCheckIn}
              className="btn-primary text-[13px] py-2 px-6 rounded-full shadow-[0_4px_14px_rgba(30,107,255,0.25)] hover:shadow-[0_6px_18px_rgba(30,107,255,0.35)] disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed"
            >
              {busy && busyAction === 'in' ? 'Checking In...' : 'Check In'}
            </button>
          )}

          {isCheckedIn && !isCheckedOut && (
            <button
              type="button"
              disabled={busy || loading}
              onClick={handleCheckOut}
              className="btn-primary text-[13px] py-2 px-6 rounded-full bg-[#1E6BFF] shadow-[0_4px_14px_rgba(30,107,255,0.25)] hover:shadow-[0_6px_18px_rgba(30,107,255,0.35)] disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed"
            >
              {busy && busyAction === 'out' ? 'Checking Out...' : 'Check Out'}
            </button>
          )}

          {isCheckedOut && (
            <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-3.5 py-1.5 text-[12px] font-bold text-emerald-700 shadow-sm">
              <CheckCircle2 size={15} className="text-emerald-600" />
              <span>Attendance Completed</span>
            </span>
          )}
        </div>
      </div>

      {/* Metrics Row */}
      <div className={`mt-4 grid grid-cols-2 ${showBurnoutMetric ? 'sm:grid-cols-3 lg:grid-cols-6' : 'sm:grid-cols-5'} gap-3 pt-3.5 border-t border-[#E2EAF2]`}>
        {/* Status */}
        <div className="flex flex-col">
          <span className="text-[11px] font-semibold text-[#64748B]">Status</span>
          <div className="mt-1">
            <span
              className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-bold tracking-tight ${
                statusTone === 'green'
                  ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                  : statusTone === 'blue'
                  ? 'border-blue-200 bg-blue-50 text-[#1E6BFF]'
                  : statusTone === 'amber'
                  ? 'border-amber-200 bg-amber-50 text-amber-700'
                  : 'border-slate-200 bg-slate-100 text-[#64748B]'
              }`}
            >
              {statusText}
            </span>
          </div>
        </div>

        {/* Check-in time */}
        <div className="flex flex-col">
          <span className="text-[11px] font-semibold text-[#64748B]">Check-in</span>
          <span className="mt-1 text-[13px] font-bold text-[#0D192B]">
            {att?.checkInTime || '—'}
          </span>
        </div>

        {/* Check-out time */}
        <div className="flex flex-col">
          <span className="text-[11px] font-semibold text-[#64748B]">Check-out</span>
          <span className="mt-1 text-[13px] font-bold text-[#0D192B]">
            {att?.checkOutTime || '—'}
          </span>
        </div>

        {/* Working Hours */}
        <div className="flex flex-col">
          <span className="text-[11px] font-semibold text-[#64748B]">Working Hours</span>
          <span className="mt-1 text-[13px] font-bold text-[#0D192B]">
            {workingHoursDisplay}
          </span>
        </div>

        {/* Overtime */}
        <div className="flex flex-col">
          <span className="text-[11px] font-semibold text-[#64748B]">Overtime</span>
          <span className="mt-1 text-[13px] font-bold text-[#0D192B]">
            {overtimeDisplay}
          </span>
        </div>

        {/* Burnout Risk (Manager & Supported Roles) */}
        {showBurnoutMetric && (
          <div
            className={`flex flex-col ${onOpenDetails ? 'cursor-pointer group' : ''}`}
            onClick={onOpenDetails}
            title={onOpenDetails ? 'Click to view personal burnout risk analysis & recommendations' : undefined}
          >
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-[#64748B]">Burnout Risk</span>
              {onOpenDetails && (
                <span className="text-[10px] font-bold text-[#1E6BFF] group-hover:underline">
                  Details →
                </span>
              )}
            </div>
            <div className="mt-1 flex items-center gap-1.5">
              <span className="text-[13px] font-bold text-[#0D192B]">
                {burnoutScore}
              </span>
              <RiskBadge score={burnoutScore} />
            </div>
          </div>
        )}
      </div>

      {/* Manager AI Wellbeing Recommendation Directive */}
      {roleLabel === 'Manager' && topRec && (
        <div className="mt-3.5 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-blue-100 bg-blue-50/50 px-3.5 py-2 text-[12px] text-slate-700">
          <div className="flex items-center gap-2 min-w-0">
            <span className="shrink-0 rounded bg-blue-100 text-[#1E6BFF] text-[10px] font-bold px-1.5 py-0.5 uppercase tracking-wide">
              AI Recommendation
            </span>
            <span className="truncate text-slate-600 font-medium text-xs">
              {topRec}
            </span>
          </div>
          {onOpenDetails && (
            <button
              type="button"
              onClick={onOpenDetails}
              className="text-[11px] font-bold text-[#1E6BFF] hover:underline whitespace-nowrap ml-auto cursor-pointer"
            >
              View Analysis →
            </button>
          )}
        </div>
      )}

      {/* Success / Error Feedback Messages */}
      {msg && (
        <div className="mt-3.5 flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-[12px] font-medium text-emerald-700 fade-in">
          <CheckCircle2 size={14} className="shrink-0 text-emerald-600" />
          <span>{msg}</span>
        </div>
      )}

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
                submitting={busy && busyAction === 'in'}
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
                submitting={busy && busyAction === 'out'}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
