import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import MorningCheckIn from '../../components/survey/MorningCheckIn'
import EveningCheckOut from '../../components/survey/EveningCheckOut'
import ExpectedActualComparison from '../../components/survey/ExpectedActualComparison'
import { expectedActualToday } from '../../data/chartData'
import { submitEveningCheckOut, submitMorningCheckIn, submitPulseSurvey, getSurveyToday, checkIn, checkOut } from '../../services/api'
import { useDay } from '../../context/DayContext'
import StatusBadge from '../../components/common/StatusBadge'

export default function CheckIn() {
  const day = useDay()
  const nav = useNavigate()
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [pulseValue, setPulseValue] = useState(null)
  const [pulseDone, setPulseDone] = useState(false)
  const [successMsg, setSuccessMsg] = useState('')

  const [expectedActual, setExpectedActual] = useState([])

  useEffect(() => {
    getSurveyToday().then((res) => {
      if (res.pulseCompleted) {
        setPulseDone(true)
        setPulseValue(res.pulseValue)
      }
      if (res.expectedActualToday) {
        setExpectedActual(res.expectedActualToday)
      }
    }).catch(() => {})
  }, [])

  const morningDone = !!day.morning || ['WORKING', 'EVENING_SURVEY_PENDING', 'DAY_COMPLETED'].includes(day.phase)
  const eveningDone = day.phase === 'DAY_COMPLETED'

  async function onMorning(answers) {
    setSubmitting(true)
    setError('')
    try {
      await submitMorningCheckIn(answers)
      if (!day.checkInTime) {
        try {
          const attRes = await checkIn({ answers })
          if (attRes?.time) day.doCheckIn(attRes.time)
        } catch {
          /* ignore duplicate */
        }
      }
      day.completeMorning(answers)
      setSuccessMsg('Start-of-day survey saved successfully. Wellbeing indicators updated.')
      window.dispatchEvent(new CustomEvent('mindful-metrics-refresh'))
    } catch (e) {
      setError(e.message || 'Morning check-in could not be saved.')
    } finally {
      setSubmitting(false)
    }
  }

  async function onEvening(answers) {
    setSubmitting(true)
    setError('')
    try {
      await submitEveningCheckOut(answers)
      if (!day.checkOutTime) {
        try {
          const attRes = await checkOut({ answers, note: answers.note })
          if (attRes?.time) day.startCheckout(attRes.time, attRes.workingHours, attRes.overtime)
        } catch {
          /* ignore duplicate */
        }
      }
      day.completeEvening(answers)
      setSuccessMsg('End-of-day reflection saved successfully.')
      window.dispatchEvent(new CustomEvent('mindful-metrics-refresh'))
    } catch (e) {
      setError(e.message || 'Evening check-out could not be saved.')
    } finally {
      setSubmitting(false)
    }
  }

  async function handlePulse(level) {
    try {
      await submitPulseSurvey(level)
      setPulseValue(level)
      setPulseDone(true)
    } catch {
      /* ignore */
    }
  }

  return (
    <div className="page-stack fade-in">
      {/* 1-Question Daily Pulse Survey per Section 30 */}
      <div className="card p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Quick Daily Pulse</p>
            <p className="mt-0.5 text-sm font-medium text-slate-800">How is your workload right now?</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {['Low', 'Moderate', 'High', 'Very High'].map((lvl) => (
              <button
                key={lvl}
                type="button"
                onClick={() => handlePulse(lvl)}
                className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                  pulseValue === lvl
                    ? 'bg-[#1E6BFF] text-white shadow-sm'
                    : 'border border-[#E2EAF2] bg-white text-slate-700 hover:bg-slate-50'
                }`}
              >
                {lvl}
              </button>
            ))}
          </div>
        </div>
        {pulseDone && (
          <p className="mt-2 text-[11px] text-emerald-600">
            ✓ Logged for today: <span className="font-semibold">{pulseValue}</span> workload.
          </p>
        )}
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <div className="card flex items-center justify-between p-4">
          <div>
            <p className="text-xs text-slate-500">Daily Wellbeing Survey</p>
            <p className="text-sm font-semibold">Start-of-Day Check-in</p>
          </div>
          <StatusBadge status={morningDone ? 'Completed' : 'Pending'} />
        </div>
        <div className="card flex items-center justify-between p-4">
          <div>
            <p className="text-xs text-slate-500">End-of-Day Reflection</p>
            <p className="text-sm font-semibold">Check-out Reflection</p>
          </div>
          <StatusBadge status={eveningDone ? 'Completed' : 'Pending'} />
        </div>
      </div>

      {error && <p className="card p-4 text-sm text-red-600" role="alert">{error}</p>}
      {successMsg && <p className="card bg-emerald-50 p-4 text-sm text-emerald-700" role="alert">{successMsg}</p>}

      {day.phase === 'NOT_CHECKED_IN' && (
        <div className="card p-6">
          <p className="font-semibold text-slate-800">Start Your Day</p>
          <p className="mt-1 text-sm text-slate-500">Check in from Attendance first, then complete the daily wellbeing check-in.</p>
          <button type="button" onClick={() => nav('/employee/attendance')} className="mt-4 btn-primary">Go to Attendance</button>
        </div>
      )}

      {(day.phase === 'CHECKED_IN' || (!morningDone && day.checkInTime)) && (
        <MorningCheckIn onSubmit={onMorning} submitting={submitting} />
      )}

      {day.phase === 'WORKING' && morningDone && (
        <div className="card p-6">
          <p className="font-semibold">Morning check-in completed.</p>
          <p className="mt-1 text-sm text-slate-500">You&apos;re currently working. Evening check-out reflection pending — complete it when you finish work.</p>
        </div>
      )}

      {day.phase === 'EVENING_SURVEY_PENDING' && <EveningCheckOut onSubmit={onEvening} submitting={submitting} />}

      {day.phase === 'DAY_COMPLETED' && (
        <div className="card p-5">
          <h3 className="mb-3 text-sm font-semibold">Expected vs Actual</h3>
          <ExpectedActualComparison items={expectedActual.length ? expectedActual : expectedActualToday} />
        </div>
      )}
    </div>
  )
}
