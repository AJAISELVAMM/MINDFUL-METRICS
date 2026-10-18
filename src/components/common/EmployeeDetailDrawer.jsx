import { useEffect, useState } from 'react'
import Drawer from './Drawer'
import RiskBadge from './RiskBadge'
import StatusBadge from './StatusBadge'
import LoadingSkeleton from './LoadingSkeleton'
import { getUserFullDetails } from '../../services/api'
import {
  User,
  Mail,
  Building2,
  Calendar,
  Clock,
  CheckCircle2,
  AlertCircle,
  Briefcase,
  AlertTriangle,
  Phone,
} from 'lucide-react'

export default function EmployeeDetailDrawer({ open, employeeId, onClose }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [tab, setTab] = useState('overview')

  useEffect(() => {
    if (!open || !employeeId) {
      setData(null)
      setError(null)
      return
    }

    let active = true
    setLoading(true)
    setData(null) // Clear previous user's data immediately so stale details are never shown
    setError(null)
    setTab('overview')

    getUserFullDetails(employeeId)
      .then((res) => {
        if (active) {
          setData(res)
        }
      })
      .catch((err) => {
        if (active) {
          setData(null)
          setError(err.message || 'Failed to load user details')
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false)
        }
      })

    return () => {
      active = false
    }
  }, [open, employeeId])


  const profile = data?.profile
  const wellbeing = data?.wellbeing
  const workload = data?.workload
  const teamStats = data?.team_stats
  const attendance = data?.attendance || []
  const tasks = data?.tasks || []
  const leaves = data?.leaves || []
  const permissions = data?.permissions || []

  return (
    <Drawer
      open={open}
      title={profile?.name ? `${profile.name}` : 'Details'}
      onClose={onClose}
      width="md:w-1/2"
    >
      {loading && <LoadingSkeleton rows={4} />}

      {error && (
        <div className="card p-6 text-center text-sm text-red-600">
          <AlertCircle className="mx-auto mb-2 h-6 w-6 text-red-500" />
          <p className="font-semibold">Unable to load details</p>
          <p className="mt-1 text-xs text-slate-500">{error}</p>
        </div>
      )}

      {!loading && !error && data && (
        <div className="space-y-4 text-slate-800">
          {/* Header Profile Summary */}
          <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[#0B4F6C] text-lg font-bold text-white shadow-sm">
                  {profile.name?.charAt(0) || 'U'}
                </div>
                <div>
                  <h3 className="text-base font-semibold text-slate-900">{profile.name}</h3>
                  <p className="text-xs text-slate-500">
                    {profile.role} · <span className="font-mono text-slate-600">{profile.employee_id}</span>
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="inline-flex items-center rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-700 border border-emerald-200">
                  {profile.account_status || 'Active'}
                </span>
              </div>
            </div>

            <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2 text-xs text-slate-600 border-t border-slate-200 pt-3">
              <div className="flex items-center gap-2">
                <Building2 className="h-3.5 w-3.5 text-slate-400" />
                <span>Department: <strong className="text-slate-800">{profile.department}</strong></span>
              </div>
              <div className="flex items-center gap-2">
                <Mail className="h-3.5 w-3.5 text-slate-400" />
                <span>Email: <strong className="text-slate-800">{profile.email}</strong></span>
              </div>
              <div className="flex items-center gap-2">
                <User className="h-3.5 w-3.5 text-slate-400" />
                <span>Manager: <strong className="text-slate-800">{profile.manager}</strong></span>
              </div>
              <div className="flex items-center gap-2">
                <Phone className="h-3.5 w-3.5 text-slate-400" />
                <span>Phone: <strong className="text-slate-800">{profile.phone}</strong></span>
              </div>
            </div>
          </div>

          {/* Tab Navigation */}
          <div className="flex border-b border-slate-200 text-xs font-medium">
            <button
              type="button"
              onClick={() => setTab('overview')}
              className={`border-b-2 px-3 py-2 transition-colors ${
                tab === 'overview'
                  ? 'border-[#0B4F6C] font-semibold text-[#0B4F6C]'
                  : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              Overview & Wellbeing
            </button>
            <button
              type="button"
              onClick={() => setTab('attendance')}
              className={`border-b-2 px-3 py-2 transition-colors ${
                tab === 'attendance'
                  ? 'border-[#0B4F6C] font-semibold text-[#0B4F6C]'
                  : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              Attendance ({attendance.length})
            </button>
            <button
              type="button"
              onClick={() => setTab('tasks')}
              className={`border-b-2 px-3 py-2 transition-colors ${
                tab === 'tasks'
                  ? 'border-[#0B4F6C] font-semibold text-[#0B4F6C]'
                  : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              Tasks & Work ({tasks.length})
            </button>
            <button
              type="button"
              onClick={() => setTab('leaves')}
              className={`border-b-2 px-3 py-2 transition-colors ${
                tab === 'leaves'
                  ? 'border-[#0B4F6C] font-semibold text-[#0B4F6C]'
                  : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              Leave & Permission ({leaves.length + permissions.length})
            </button>
          </div>

          {/* TAB 1: OVERVIEW & WELLBEING */}
          {tab === 'overview' && (
            <div className="space-y-4">
              {/* Key Indicators - All 7 Core Metrics */}
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <div className="card p-3">
                  <p className="text-[11px] font-medium text-slate-500">Burnout Risk</p>
                  <div className="mt-1 flex items-center gap-1.5">
                    {wellbeing?.has_prediction && wellbeing.burnout_score !== null ? (
                      <>
                        <span className="text-lg font-bold">{wellbeing.burnout_score}</span>
                        <RiskBadge score={wellbeing.burnout_score} />
                      </>
                    ) : (
                      <span className="text-xs font-semibold text-slate-400">N/A</span>
                    )}
                  </div>
                </div>

                <div className="card p-3">
                  <p className="text-[11px] font-medium text-slate-500">Active Tasks</p>
                  <p className="mt-1 text-lg font-bold text-slate-800">
                    {workload?.active_tasks !== undefined && workload?.active_tasks !== null ? workload.active_tasks : 'N/A'}
                  </p>
                </div>

                <div className="card p-3">
                  <p className="text-[11px] font-medium text-slate-500">Completion Rate</p>
                  <p className="mt-1 text-lg font-bold text-emerald-600">
                    {workload?.completion_rate !== undefined && workload?.completion_rate !== null ? `${workload.completion_rate}%` : 'N/A'}
                  </p>
                </div>

                <div className="card p-3">
                  <p className="text-[11px] font-medium text-slate-500">Blocked Tasks</p>
                  <p className={`mt-1 text-lg font-bold ${workload?.blocked_tasks > 0 ? 'text-amber-600' : 'text-slate-800'}`}>
                    {workload?.blocked_tasks !== undefined && workload?.blocked_tasks !== null ? workload.blocked_tasks : 0}
                  </p>
                </div>

                <div className="card p-3">
                  <p className="text-[11px] font-medium text-slate-500">Workload Score</p>
                  <p className="mt-1 text-lg font-bold text-slate-800">
                    {workload?.workload_score !== undefined && workload?.workload_score !== null
                      ? workload.workload_score
                      : (wellbeing?.workload_score !== undefined && wellbeing?.workload_score !== null ? wellbeing.workload_score : 'N/A')}
                  </p>
                </div>

                <div className="card p-3">
                  <p className="text-[11px] font-medium text-slate-500">Work-Life Balance Score</p>
                  <p className="mt-1 text-lg font-bold text-slate-800">
                    {workload?.work_life_balance_score !== undefined && workload?.work_life_balance_score !== null
                      ? workload.work_life_balance_score
                      : (wellbeing?.work_life_balance_score !== undefined && wellbeing?.work_life_balance_score !== null ? wellbeing.work_life_balance_score : 'N/A')}
                  </p>
                </div>

                <div className="card p-3">
                  <p className="text-[11px] font-medium text-slate-500">Working Hours</p>
                  <p className="mt-1 text-lg font-bold text-slate-800">
                    {workload?.working_hours || (workload?.working_hours_num !== undefined && workload?.working_hours_num !== null ? `${workload.working_hours_num}h` : (wellbeing?.working_hours ?? 'N/A'))}
                  </p>
                </div>
              </div>

              {/* Manager Team Oversight */}
              {teamStats && (
                <div className="rounded-xl border border-blue-100 bg-blue-50/50 p-3">
                  <p className="text-[11px] font-bold uppercase tracking-wider text-blue-700">Team Oversight</p>
                  <div className="mt-2 grid grid-cols-3 gap-2 text-center text-xs">
                    <div className="rounded-lg bg-white p-2 border border-blue-100">
                      <p className="text-[10px] text-slate-500">Team Members</p>
                      <p className="text-base font-bold text-slate-800">{teamStats.team_members_count}</p>
                    </div>
                    <div className="rounded-lg bg-white p-2 border border-blue-100">
                      <p className="text-[10px] text-slate-500">Managed Tasks</p>
                      <p className="text-base font-bold text-slate-800">{teamStats.team_tasks_count}</p>
                    </div>
                    <div className="rounded-lg bg-white p-2 border border-blue-100">
                      <p className="text-[10px] text-slate-500">Active Tasks</p>
                      <p className="text-base font-bold text-blue-600">{teamStats.team_tasks_active}</p>
                    </div>
                  </div>
                </div>
              )}

              {/* AI Risk Factors & Recommendations */}
              {wellbeing?.has_prediction ? (
                <div className="card p-4 space-y-3">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                    Contributing Risk Factors
                  </h4>
                  {wellbeing.risk_factors?.length ? (
                    <div className="flex flex-wrap gap-2">
                      {wellbeing.risk_factors.map((f, i) => (
                        <span
                          key={i}
                          className="inline-flex items-center gap-1 rounded-md bg-slate-100 px-2.5 py-1 text-xs text-slate-700"
                        >
                          <AlertTriangle className="h-3 w-3 text-amber-500" />
                          {f.name}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-slate-500">No elevated risk factors detected.</p>
                  )}

                  {wellbeing.recommendations?.length > 0 && (
                    <div className="pt-2 border-t border-slate-100">
                      <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
                        Tailored Recommendations
                      </h4>
                      <ul className="space-y-1.5 text-xs text-slate-600">
                        {wellbeing.recommendations.map((rec, i) => (
                          <li key={i} className="flex items-start gap-1.5">
                            <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-emerald-500" />
                            <span>{rec}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ) : (
                <div className="card p-4 text-center text-xs text-slate-400">
                  Burnout prediction is currently unavailable for this user.
                </div>
              )}
            </div>
          )}

          {/* TAB 2: ATTENDANCE HISTORY */}
          {tab === 'attendance' && (
            <div className="space-y-3">
              {attendance.length ? (
                <div className="max-h-96 overflow-y-auto rounded-lg border border-slate-200">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-50 text-slate-600 border-b border-slate-200">
                      <tr>
                        <th className="p-2.5">Date</th>
                        <th className="p-2.5">Check In</th>
                        <th className="p-2.5">Check Out</th>
                        <th className="p-2.5">Hours</th>
                        <th className="p-2.5">Overtime</th>
                        <th className="p-2.5">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 text-slate-700">
                      {attendance.map((a, i) => (
                        <tr key={i} className="hover:bg-slate-50/50">
                          <td className="p-2.5 font-medium">{a.date}</td>
                          <td className="p-2.5">{a.check_in}</td>
                          <td className="p-2.5">{a.check_out}</td>
                          <td className="p-2.5">{a.working_hours}</td>
                          <td className="p-2.5">{a.overtime}</td>
                          <td className="p-2.5">
                            <span className={`inline-block rounded px-1.5 py-0.5 text-[10px] font-medium ${
                              a.status?.toLowerCase().includes('present')
                                ? 'bg-emerald-50 text-emerald-700'
                                : a.status?.toLowerCase().includes('leave')
                                ? 'bg-amber-50 text-amber-700'
                                : 'bg-slate-100 text-slate-600'
                            }`}>
                              {a.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="card p-6 text-center text-xs text-slate-400">
                  No attendance records found for this employee.
                </div>
              )}
            </div>
          )}

          {/* TAB 3: TASKS & PROGRESS */}
          {tab === 'tasks' && (
            <div className="space-y-2.5">
              {tasks.length ? (
                tasks.map((t) => (
                  <div key={t.id} className="card p-3 space-y-2 text-xs">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <p className="font-semibold text-slate-900">{t.title}</p>
                        {t.description && <p className="text-slate-500 mt-0.5 line-clamp-2">{t.description}</p>}
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${
                          t.priority === 'High' ? 'bg-rose-50 text-rose-700' : 'bg-slate-100 text-slate-700'
                        }`}>
                          {t.priority}
                        </span>
                        <StatusBadge status={t.status} />
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <div className="h-1.5 flex-1 rounded-full bg-slate-100 overflow-hidden">
                        <div
                          className="h-full bg-[#0B4F6C] rounded-full transition-all"
                          style={{ width: `${Math.min(100, t.progress || 0)}%` }}
                        />
                      </div>
                      <span className="font-medium text-slate-600">{t.progress || 0}%</span>
                    </div>

                    <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1">
                      <span>Deadline: <strong className="text-slate-700">{t.deadline}</strong></span>
                      {t.blockers && (
                        <span className="text-amber-600 font-medium">Blocker: {t.blockers}</span>
                      )}
                    </div>
                  </div>
                ))
              ) : (
                <div className="card p-6 text-center text-xs text-slate-400">
                  No tasks assigned to this employee.
                </div>
              )}
            </div>
          )}

          {/* TAB 4: LEAVE & PERMISSIONS */}
          {tab === 'leaves' && (
            <div className="space-y-4">
              <div>
                <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Leave History ({leaves.length})
                </h4>
                {leaves.length ? (
                  <div className="space-y-2">
                    {leaves.map((l) => (
                      <div key={l.id} className="card p-2.5 flex items-center justify-between text-xs">
                        <div>
                          <p className="font-semibold text-slate-800">{l.type} · <span className="font-normal text-slate-500">{l.duration}</span></p>
                          <p className="text-[11px] text-slate-500">{l.dates} · Reason: {l.reason}</p>
                        </div>
                        <StatusBadge status={l.status} />
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-400">No leave requests found.</p>
                )}
              </div>

              <div className="pt-2 border-t border-slate-100">
                <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Permission Requests ({permissions.length})
                </h4>
                {permissions.length ? (
                  <div className="space-y-2">
                    {permissions.map((p) => (
                      <div key={p.id} className="card p-2.5 flex items-center justify-between text-xs">
                        <div>
                          <p className="font-semibold text-slate-800">Early Checkout at {p.requested_checkout_time}</p>
                          <p className="text-[11px] text-slate-500">{p.date} · Reason: {p.reason}</p>
                        </div>
                        <StatusBadge status={p.status} />
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-400">No permission requests found.</p>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </Drawer>
  )
}
