import { useEffect, useState } from 'react'
import StatCard from '../../components/common/StatCard'
import DataTable from '../../components/common/DataTable'
import StatusBadge from '../../components/common/StatusBadge'
import {
  getHRAttendance,
  getAttendanceCorrections,
  approveAttendanceCorrection,
  rejectAttendanceCorrection,
  getHolidays,
} from '../../services/api'
import LoadingSkeleton from '../../components/common/LoadingSkeleton'
import ErrorState from '../../components/common/ErrorState'

export default function HRAttendance() {
  const [rows, setRows] = useState([])
  const [corrections, setCorrections] = useState([])
  const [holidays, setHolidays] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [successMsg, setSuccessMsg] = useState('')
  const [filterDept, setFilterDept] = useState('All')
  const [filterStatus, setFilterStatus] = useState('All')
  const [filterDate, setFilterDate] = useState(() => new Date().toISOString().split('T')[0])
  const [activeTab, setActiveTab] = useState('log') // 'log', 'corrections', 'holidays'
  const [actionBusy, setActionBusy] = useState(false)

  useEffect(() => {
    loadAllData()
  }, [filterDept, filterStatus, filterDate])

  async function loadAllData() {
    setLoading(true)
    setError('')
    try {
      const [attData, corrData, holData] = await Promise.all([
        getHRAttendance({
          department: filterDept !== 'All' ? filterDept : undefined,
          status: filterStatus !== 'All' ? filterStatus : undefined,
          date: filterDate,
        }),
        getAttendanceCorrections().catch(() => []),
        getHolidays().catch(() => []),
      ])
      setRows(attData || [])
      setCorrections(corrData || [])
      setHolidays(holData || [])
    } catch {
      setError('Could not load organization attendance.')
    } finally {
      setLoading(false)
    }
  }

  async function handleApprove(id) {
    if (!confirm('Approve this attendance correction request?')) return
    setActionBusy(true)
    setError('')
    setSuccessMsg('')
    try {
      const res = await approveAttendanceCorrection(id)
      setSuccessMsg(res.message || 'Correction approved successfully.')
      await loadAllData()
      window.dispatchEvent(new CustomEvent('mindful-metrics-refresh'))
    } catch (e) {
      setError(e.message || 'Could not approve correction.')
    } finally {
      setActionBusy(false)
    }
  }

  async function handleReject(id) {
    const reason = prompt('Enter rejection reason (optional):', 'Correction details could not be verified.')
    if (reason === null) return
    setActionBusy(true)
    setError('')
    setSuccessMsg('')
    try {
      const res = await rejectAttendanceCorrection(id, reason)
      setSuccessMsg(res.message || 'Correction rejected.')
      await loadAllData()
    } catch (e) {
      setError(e.message || 'Could not reject correction.')
    } finally {
      setActionBusy(false)
    }
  }

  const isPresent = (r) => r.status === 'PRESENT' || r.display_status === 'Present' || r.status === 'Present'
  const isAbsent = (r) => r.status === 'ABSENT' || r.display_status === 'Absent' || r.status === 'Absent'
  const isLateOrException = (r) =>
    r.status === 'LATE' ||
    r.status === 'HALF_DAY' ||
    r.status === 'EXCEPTION' ||
    r.status?.includes('Late') ||
    r.status?.includes('Half') ||
    r.display_status?.includes('Late') ||
    r.display_status?.includes('Half')

  const presentCount = rows.filter(isPresent).length
  const absentCount = rows.filter(isAbsent).length
  const lateCount = rows.filter(isLateOrException).length
  const pendingCorrectionsCount = corrections.filter((c) => c.status?.toUpperCase() === 'PENDING').length

  const isToday = filterDate === new Date().toISOString().split('T')[0]

  return (
    <div className="page-stack fade-in">
      {error && <p className="text-sm text-red-600" role="alert">{error}</p>}
      {successMsg && (
        <p className="rounded-lg bg-emerald-50 p-2.5 text-sm text-emerald-700" role="alert">
          {successMsg}
        </p>
      )}

      <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
        <StatCard label="Total Monitored" value={rows.length} tone="blue" />
        <StatCard label={isToday ? "Present Today" : "Present"} value={presentCount} tone="low" />
        <StatCard label="Absent" value={absentCount} />
        <StatCard label="Late / Exceptions" value={lateCount} tone="mod" />
        <StatCard label="Pending Corrections" value={pendingCorrectionsCount} tone={pendingCorrectionsCount > 0 ? 'mod' : 'default'} />
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-slate-200 pb-2">
        <button
          type="button"
          onClick={() => setActiveTab('log')}
          className={`px-3 py-1.5 text-xs font-semibold rounded-md transition ${
            activeTab === 'log' ? 'bg-[#0F2035] text-white' : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          Attendance Log
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('corrections')}
          className={`px-3 py-1.5 text-xs font-semibold rounded-md transition flex items-center gap-1.5 ${
            activeTab === 'corrections' ? 'bg-[#0F2035] text-white' : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          Correction Requests
          {pendingCorrectionsCount > 0 && (
            <span className="inline-flex items-center justify-center h-4 w-4 rounded-full bg-amber-500 text-[10px] text-white font-bold">
              {pendingCorrectionsCount}
            </span>
          )}
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('holidays')}
          className={`px-3 py-1.5 text-xs font-semibold rounded-md transition ${
            activeTab === 'holidays' ? 'bg-[#0F2035] text-white' : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          2026 TN Public Holidays ({holidays.length})
        </button>
      </div>

      {activeTab === 'log' && (
        <>
          <div className="card p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Organization Attendance Log
              </p>
              <div className="flex flex-wrap gap-2">
                <input
                  type="date"
                  value={filterDate}
                  onChange={(e) => setFilterDate(e.target.value)}
                  className="ww-input mt-0 text-xs max-w-[130px]"
                />
                <select
                  value={filterDept}
                  onChange={(e) => setFilterDept(e.target.value)}
                  className="ww-input mt-0 text-xs max-w-[150px]"
                >
                  <option value="All">All Departments</option>
                  <option>Engineering</option>
                  <option>Marketing</option>
                  <option>Finance</option>
                  <option>Operations</option>
                  <option>Testing</option>
                  <option>Design</option>
                  <option>Support</option>
                  <option>HR</option>
                  <option>Sales</option>
                </select>
                <select
                  value={filterStatus}
                  onChange={(e) => setFilterStatus(e.target.value)}
                  className="ww-input mt-0 text-xs max-w-[140px]"
                >
                  <option value="All">All Statuses</option>
                  <option>Present</option>
                  <option>Absent</option>
                  <option>Late</option>
                  <option>On Leave</option>
                </select>
              </div>
            </div>
          </div>

          <div className="card p-4">
            {loading ? (
              <LoadingSkeleton rows={3} />
            ) : (
              <DataTable
                columns={[
                  {
                    key: 'name',
                    label: 'Employee',
                    render: (r) => (
                      <div>
                        <p className="font-semibold text-slate-800">{r.name}</p>
                        <p className="text-[11px] text-slate-400">{r.id}</p>
                      </div>
                    ),
                  },
                  { key: 'dept', label: 'Department' },
                  { key: 'role', label: 'Role' },
                  {
                    key: 'status',
                    label: 'Status',
                    render: (r) => <StatusBadge status={r.status} />,
                  },
                  { key: 'checkIn', label: 'Check-in' },
                  { key: 'checkOut', label: 'Check-out' },
                  { key: 'hours', label: 'Working Hours' },
                  { key: 'overtime', label: 'Overtime' },
                ]}
                rows={rows}
              />
            )}
          </div>
        </>
      )}

      {activeTab === 'corrections' && (
        <div className="card p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-slate-800">
              Employee Attendance Correction Requests
            </h3>
            <span className="text-xs text-slate-400">
              {corrections.length} total request{corrections.length === 1 ? '' : 's'}
            </span>
          </div>
          {corrections.length === 0 ? (
            <p className="p-4 text-xs text-slate-400 text-center">No correction requests found.</p>
          ) : (
            <DataTable
              columns={[
                {
                  key: 'employee_name',
                  label: 'Employee',
                  render: (r) => (
                    <div>
                      <p className="font-semibold text-slate-800">{r.employee_name}</p>
                      <p className="text-[11px] text-slate-400">{r.employee_code} • {r.department}</p>
                    </div>
                  ),
                },
                { key: 'attendance_date', label: 'Date' },
                { key: 'reason', label: 'Reason' },
                {
                  key: 'requested_times',
                  label: 'Requested Hours',
                  render: (r) => `${r.requested_check_in} – ${r.requested_check_out}`,
                },
                {
                  key: 'status',
                  label: 'Status',
                  render: (r) => <StatusBadge status={r.status} />,
                },
                {
                  key: 'actions',
                  label: 'Action',
                  render: (r) =>
                    r.status === 'Pending' ? (
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          disabled={actionBusy}
                          onClick={() => handleApprove(r.id)}
                          className="px-2.5 py-1 text-xs font-medium text-emerald-700 bg-emerald-50 hover:bg-emerald-100 rounded border border-emerald-200 transition disabled:opacity-50"
                        >
                          Approve
                        </button>
                        <button
                          type="button"
                          disabled={actionBusy}
                          onClick={() => handleReject(r.id)}
                          className="px-2.5 py-1 text-xs font-medium text-rose-700 bg-rose-50 hover:bg-rose-100 rounded border border-rose-200 transition disabled:opacity-50"
                        >
                          Reject
                        </button>
                      </div>
                    ) : (
                      <span className="text-xs text-slate-400">
                        {r.reviewed_by_name ? `By ${r.reviewed_by_name}` : 'Processed'}
                      </span>
                    ),
                },
              ]}
              rows={corrections}
            />
          )}
        </div>
      )}

      {activeTab === 'holidays' && (
        <div className="card p-4">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 className="text-sm font-semibold text-slate-800">
                2026 Tamil Nadu Government Public Holidays
              </h3>
              <p className="text-xs text-slate-500">
                G.O.(Ms.) No. 708, Public (Miscellaneous) Department, Dated 11.11.2025 • Negotiable Instruments Act, 1881
              </p>
            </div>
            <span className="text-xs font-semibold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800">
              Verified in Supabase DB
            </span>
          </div>
          <DataTable
            columns={[
              {
                key: 'sno',
                label: '#',
                render: (_, __, i) => <span className="text-xs text-slate-400">{i + 1}</span>,
              },
              { key: 'holiday_name', label: 'Holiday Name' },
              { key: 'holiday_date', label: 'Date' },
              {
                key: 'holiday_type',
                label: 'Type',
                render: (r) => (
                  <span
                    className={`inline-block px-2 py-0.5 rounded text-[11px] font-medium ${
                      r.holiday_type === 'Bank Holiday'
                        ? 'bg-amber-50 text-amber-700 border border-amber-200'
                        : 'bg-indigo-50 text-indigo-700 border border-indigo-200'
                    }`}
                  >
                    {r.holiday_type}
                  </span>
                ),
              },
              {
                key: 'applicability',
                label: 'Applicability',
                render: (r) => (
                  <span className="text-xs font-medium text-slate-600">
                    {r.applicability === 'bank_only' ? 'Banks Only' : 'All Employees'}
                  </span>
                ),
              },
            ]}
            rows={holidays}
          />
        </div>
      )}
    </div>
  )
}
