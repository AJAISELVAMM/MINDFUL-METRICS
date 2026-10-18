import { useState, useEffect, useRef } from 'react'
import { ChevronLeft, ChevronRight, Calendar as CalendarIcon, Clock, CheckCircle2, AlertCircle, Sun } from 'lucide-react'
import { getAttendanceCalendar } from '../../services/api'
import StatusBadge from './StatusBadge'

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
]

const WEEKDAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

export default function AttendanceCalendar({ userId = null, onSelectDate = null }) {
  const today = new Date()
  const [currentYear, setCurrentYear] = useState(today.getFullYear())
  const [currentMonth, setCurrentMonth] = useState(today.getMonth() + 1) // 1-12
  const [days, setDays] = useState([])
  const [loading, setLoading] = useState(false)
  const [selectedDay, setSelectedDay] = useState(null)
  const reqSeq = useRef(0)

  useEffect(() => {
    loadCalendar(currentYear, currentMonth)
  }, [currentYear, currentMonth, userId])

  async function loadCalendar(year, month) {
    const seq = ++reqSeq.current
    setLoading(true)
    try {
      const data = await getAttendanceCalendar({ year, month, user_id: userId })
      if (seq === reqSeq.current) {
        setDays(data || [])
        // If today is in this month, select today by default
        const todayStr = `${year}-${String(month).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`
        const match = data?.find(d => d.date === todayStr)
        if (match && !selectedDay) {
          setSelectedDay(match)
        }
      }
    } catch {
      if (seq === reqSeq.current) {
        setDays([])
      }
    } finally {
      if (seq === reqSeq.current) {
        setLoading(false)
      }
    }
  }

  function handlePrevMonth() {
    if (currentMonth === 1) {
      setCurrentMonth(12)
      setCurrentYear(y => y - 1)
    } else {
      setCurrentMonth(m => m - 1)
    }
  }

  function handleNextMonth() {
    if (currentMonth === 12) {
      setCurrentMonth(1)
      setCurrentYear(y => y + 1)
    } else {
      setCurrentMonth(m => m + 1)
    }
  }

  function handleToday() {
    const now = new Date()
    setCurrentYear(now.getFullYear())
    setCurrentMonth(now.getMonth() + 1)
  }

  // Calculate leading blanks for the first day of the month
  // JavaScript getDay(): Sunday = 0, Monday = 1, ...
  const firstDayOfMonth = new Date(currentYear, currentMonth - 1, 1).getDay()
  // Adjust to Monday = 0, Sunday = 6
  const leadingBlanks = (firstDayOfMonth + 6) % 7

  const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`

  return (
    <div className="card p-4 sm:p-5">
      {/* Calendar Header with Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4 border-b border-slate-100 pb-3">
        <div className="flex items-center gap-2">
          <CalendarIcon className="h-5 w-5 text-indigo-600" />
          <h3 className="text-base font-semibold text-slate-800">
            Attendance Calendar
          </h3>
          <span className="text-xs font-medium text-slate-400">
            ({MONTH_NAMES[currentMonth - 1]} {currentYear})
          </span>
        </div>

        <div className="flex items-center gap-1.5 sm:gap-2">
          <button
            type="button"
            onClick={handleToday}
            className="px-2.5 py-1 text-xs font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-md transition"
          >
            Today
          </button>
          <div className="flex items-center rounded-md border border-slate-200 bg-white shadow-xs">
            <button
              type="button"
              onClick={handlePrevMonth}
              aria-label="Previous month"
              className="p-1.5 text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition rounded-l-md"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <span className="px-3 py-1 text-xs font-semibold text-slate-700 min-w-[110px] text-center border-x border-slate-100">
              {MONTH_NAMES[currentMonth - 1].slice(0, 3)} {currentYear}
            </span>
            <button
              type="button"
              onClick={handleNextMonth}
              aria-label="Next month"
              className="p-1.5 text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition rounded-r-md"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Weekday headers */}
      <div className="grid grid-cols-7 gap-1 sm:gap-1.5 text-center text-xs font-semibold text-slate-500 mb-1">
        {WEEKDAY_NAMES.map((w, idx) => (
          <div
            key={w}
            className={`py-1.5 rounded-sm ${idx === 6 ? 'text-purple-600 bg-purple-50/50' : 'bg-slate-50'}`}
          >
            {w}
          </div>
        ))}
      </div>

      {/* Days Grid */}
      {loading ? (
        <div className="h-64 flex items-center justify-center">
          <div className="animate-spin h-6 w-6 border-2 border-indigo-600 border-t-transparent rounded-full" />
        </div>
      ) : (
        <div className="grid grid-cols-7 gap-1 sm:gap-1.5">
          {/* Empty cells before first day */}
          {Array.from({ length: leadingBlanks }).map((_, i) => (
            <div key={`blank-${i}`} className="min-h-[64px] sm:min-h-[72px] bg-slate-50/40 rounded-md border border-dashed border-slate-100" />
          ))}

          {/* Days of the month */}
          {days.map((item) => {
            const isToday = item.date === todayStr
            const isSelected = selectedDay && selectedDay.date === item.date

            // Badge styling
            let badgeClass = 'bg-slate-100 text-slate-600'
            let dotClass = 'bg-slate-400'

            if (item.status === 'PRESENT') {
              badgeClass = 'bg-emerald-50 text-emerald-700 border border-emerald-200'
              dotClass = 'bg-emerald-500'
            } else if (item.status === 'HALF_DAY') {
              badgeClass = 'bg-amber-50 text-amber-700 border border-amber-200'
              dotClass = 'bg-amber-500'
            } else if (item.status === 'LATE') {
              badgeClass = 'bg-amber-50 text-amber-700 border border-amber-200'
              dotClass = 'bg-amber-500'
            } else if (item.status === 'ABSENT') {
              badgeClass = 'bg-rose-50 text-rose-700 border border-rose-200'
              dotClass = 'bg-rose-500'
            } else if (item.status === 'WEEKLY_OFF') {
              badgeClass = 'bg-purple-50 text-purple-700 border border-purple-200'
              dotClass = 'bg-purple-500'
            } else if (item.status === 'HOLIDAY') {
              badgeClass = 'bg-indigo-50 text-indigo-700 border border-indigo-200'
              dotClass = 'bg-indigo-500'
            } else if (item.status === 'ON_LEAVE' || item.status === 'LEAVE') {
              badgeClass = 'bg-blue-50 text-blue-700 border border-blue-200'
              dotClass = 'bg-blue-500'
            } else if (item.status === 'FUTURE') {
              badgeClass = 'bg-slate-50 text-slate-400 border border-slate-200'
              dotClass = 'bg-slate-300'
            } else if (item.status === 'PENDING') {
              badgeClass = 'bg-cyan-50 text-cyan-700 border border-cyan-200'
              dotClass = 'bg-cyan-500'
            }

            return (
              <button
                key={item.date}
                type="button"
                onClick={() => {
                  setSelectedDay(item)
                  if (onSelectDate) onSelectDate(item)
                }}
                className={`relative flex flex-col justify-between p-1.5 sm:p-2 text-left rounded-md border transition min-h-[64px] sm:min-h-[72px] ${
                  isSelected
                    ? 'border-indigo-600 ring-2 ring-indigo-500/20 bg-indigo-50/20'
                    : isToday
                    ? 'border-indigo-400 bg-indigo-50/10'
                    : 'border-slate-200 bg-white hover:bg-slate-50'
                }`}
              >
                <div className="flex items-center justify-between w-full">
                  <span
                    className={`inline-flex items-center justify-center text-xs font-bold h-5 w-5 rounded-full ${
                      isToday
                        ? 'bg-indigo-600 text-white'
                        : item.isWeeklyOff
                        ? 'text-purple-700'
                        : 'text-slate-700'
                    }`}
                  >
                    {item.day}
                  </span>
                  <span className={`h-1.5 w-1.5 rounded-full ${dotClass}`} />
                </div>

                <div className="mt-1 w-full">
                  <span
                    title={item.badge}
                    className={`block w-full truncate rounded px-1 py-0.5 text-[10px] font-medium leading-tight text-center ${badgeClass}`}
                  >
                    {item.isHoliday
                      ? item.holidayName || 'Holiday'
                      : item.status === 'PRESENT' && item.checkIn
                      ? item.checkIn
                      : item.badge}
                  </span>
                </div>
              </button>
            )
          })}
        </div>
      )}

      {/* Selected Day Details Panel */}
      {selectedDay && (
        <div className="mt-4 rounded-lg bg-slate-50 border border-slate-200 p-3.5 sm:p-4 text-xs">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-2.5 mb-2.5">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-sm text-slate-800">
                {selectedDay.date} ({selectedDay.weekday})
              </span>
              <StatusBadge status={selectedDay.status} />
            </div>
            {selectedDay.isHoliday && (
              <span className="inline-flex items-center gap-1 rounded bg-indigo-100 px-2 py-0.5 text-[11px] font-semibold text-indigo-800">
                <Sun className="h-3 w-3" />
                {selectedDay.holidayName}
              </span>
            )}
            {selectedDay.isWeeklyOff && (
              <span className="inline-flex items-center gap-1 rounded bg-purple-100 px-2 py-0.5 text-[11px] font-semibold text-purple-800">
                Weekly Off (Sunday)
              </span>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div>
              <p className="text-slate-400">Check-In</p>
              <p className="font-semibold text-slate-700 mt-0.5">{selectedDay.checkIn || '—'}</p>
            </div>
            <div>
              <p className="text-slate-400">Check-Out</p>
              <p className="font-semibold text-slate-700 mt-0.5">{selectedDay.checkOut || '—'}</p>
            </div>
            <div>
              <p className="text-slate-400">Working Hours</p>
              <p className="font-semibold text-slate-700 mt-0.5">{selectedDay.workingHours || '—'}</p>
            </div>
            <div>
              <p className="text-slate-400">Lateness</p>
              <p className="font-semibold text-slate-700 mt-0.5">
                {selectedDay.lateMinutes > 0 ? `${selectedDay.lateMinutes} mins late` : 'On time'}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
