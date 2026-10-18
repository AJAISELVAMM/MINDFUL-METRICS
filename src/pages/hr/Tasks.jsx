import { useEffect, useState, useMemo } from 'react'
import { Plus, Search, Eye, ListChecks, CheckCircle2, AlertTriangle, ShieldCheck } from 'lucide-react'
import StatCard from '../../components/common/StatCard'
import DataTable from '../../components/common/DataTable'
import StatusBadge from '../../components/common/StatusBadge'
import Modal from '../../components/common/Modal'
import LoadingSkeleton from '../../components/common/LoadingSkeleton'
import ErrorState from '../../components/common/ErrorState'
import {
  getHRTasks,
  createTask,
  getEmployees,
  getHRUnblockRequests,
  approveTaskUnblock,
  clarifyTaskUnblock,
  rejectTaskUnblock,
  getHRVerificationQueue,
  verifyTask,
  requestTaskChanges,
} from '../../services/api'

export default function HRTasks() {
  const [activeTab, setActiveTab] = useState('all_tasks') // 'all_tasks' | 'unblock_requests' | 'verification_queue'
  const [data, setData] = useState(null)
  const [unblockRequests, setUnblockRequests] = useState([])
  const [verificationQueue, setVerificationQueue] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [managers, setManagers] = useState([])

  // Modals
  const [openCreate, setOpenCreate] = useState(false)
  const [selectedTask, setSelectedTask] = useState(null)

  // Unblock review modal
  const [selectedUnblock, setSelectedUnblock] = useState(null)
  const [unblockDecisionReason, setUnblockDecisionReason] = useState('Approved deadline extension')
  const [clarifyMessage, setClarifyMessage] = useState('')
  const [clarifyError, setClarifyError] = useState('')

  // Verification modal
  const [selectedVerifyTask, setSelectedVerifyTask] = useState(null)
  const [verifyNotes, setVerifyNotes] = useState('')
  const [changesNotes, setChangesNotes] = useState('')
  const [changesError, setChangesError] = useState('')


  // Filters for All Tasks
  const [searchQuery, setSearchQuery] = useState('')
  const [filterStatus, setFilterStatus] = useState('All')
  const [filterPriority, setFilterPriority] = useState('All')
  const [filterManager, setFilterManager] = useState('All')

  // Form for HR assigning task
  const [form, setForm] = useState({
    name: '',
    description: '',
    priority: 'Medium',
    deadline: 'Upcoming',
    difficulty: 3,
    assigned_to: '',
  })

  useEffect(() => {
    loadAll()
  }, [])

  async function loadAll(skipManagers = false) {
    if (!skipManagers) setLoading(true)
    setError('')
    try {
      const promises = [
        getHRTasks().catch(() => ({ summary: {}, tasks: [] })),
        getHRUnblockRequests().catch(() => []),
        getHRVerificationQueue().catch(() => []),
      ]
      if (!skipManagers && managers.length === 0) {
        promises.push(getEmployees().catch(() => []))
      }
      const results = await Promise.all(promises)
      const tasksRes = results[0]
      const unblocksRes = results[1]
      const verifyRes = results[2]
      const empsRes = results[3]

      setData(tasksRes)
      setUnblockRequests(Array.isArray(unblocksRes) ? unblocksRes : [])
      setVerificationQueue(Array.isArray(verifyRes) ? verifyRes : [])

      if (empsRes) {
        const mgrList = (Array.isArray(empsRes) ? empsRes : []).filter(
          (u) => (u.role || '').toLowerCase() === 'manager'
        )
        const activeManagers = mgrList.length > 0 ? mgrList : empsRes.filter((u) => u.employee_id?.startsWith('M') || u.name?.includes('Priya'))
        setManagers(activeManagers)

        if (activeManagers.length > 0 && !form.assigned_to) {
          setForm((f) => ({ ...f, assigned_to: activeManagers[0].id || activeManagers[0].employee_id }))
        }
      }
    } catch (e) {
      setError(e.message || 'Could not load organizational task data.')
    } finally {
      setLoading(false)
    }
  }

  async function handleAssignTask(e) {
    e.preventDefault()
    if (busy) return
    if (!form.name.trim()) return
    if (!form.assigned_to) {
      setError('Please select a manager to assign this task to.')
      return
    }
    setBusy(true)
    setError('')
    try {
      await createTask(form)
      setOpenCreate(false)
      setForm({
        name: '',
        description: '',
        priority: 'Medium',
        deadline: 'Upcoming',
        difficulty: 3,
        assigned_to: managers[0]?.id || managers[0]?.employee_id || '',
      })
      await loadAll(true)
    } catch (err) {
      setError(err.message || 'Could not assign task to manager.')
    } finally {
      setBusy(false)
    }
  }

  // HR Unblock Actions
  async function handleApproveUnblock() {
    if (!selectedUnblock || busy) return
    setBusy(true)
    const reqId = selectedUnblock.id
    try {
      // Optimistic update
      setUnblockRequests(prev => prev.filter(r => r.id !== reqId))
      setSelectedUnblock(null)
      await approveTaskUnblock(reqId, unblockDecisionReason || 'Approved extension by HR')
      await loadAll(true)
      window.dispatchEvent(new CustomEvent('mindful-metrics-refresh'))
    } catch (err) {
      alert(err.message || 'Could not approve unblock request.')
      await loadAll(true)
    } finally {
      setBusy(false)
    }
  }

  async function handleClarifyUnblock() {
    if (!selectedUnblock || busy) return
    if (!clarifyMessage.trim()) {
      setClarifyError('Please enter a clarification question before asking for details.')
      return
    }
    setClarifyError('')
    setBusy(true)
    const reqId = selectedUnblock.id
    try {
      await clarifyTaskUnblock(reqId, clarifyMessage.trim())
      setSelectedUnblock(null)
      setClarifyMessage('')
      await loadAll(true)
      window.dispatchEvent(new CustomEvent('mindful-metrics-refresh'))
    } catch (err) {
      alert(err.message || 'Could not send clarification request.')
    } finally {
      setBusy(false)
    }
  }

  async function handleRejectUnblock() {
    if (!selectedUnblock || busy) return
    if (!unblockDecisionReason.trim()) {
      alert('Please provide a reason for rejecting the unblock request.')
      return
    }
    setBusy(true)
    const reqId = selectedUnblock.id
    try {
      // Optimistic update
      setUnblockRequests(prev => prev.filter(r => r.id !== reqId))
      setSelectedUnblock(null)
      await rejectTaskUnblock(reqId, unblockDecisionReason.trim())
      await loadAll(true)
      window.dispatchEvent(new CustomEvent('mindful-metrics-refresh'))
    } catch (err) {
      alert(err.message || 'Could not reject unblock request.')
      await loadAll(true)
    } finally {
      setBusy(false)
    }
  }

  // HR Verification Actions
  async function handleVerifyTask() {
    if (!selectedVerifyTask || busy) return
    setBusy(true)
    const targetTaskId = selectedVerifyTask.id
    try {
      // Optimistic removal from queue for instant feedback
      setVerificationQueue(prev => prev.filter(t => t.id !== targetTaskId && t.raw_id !== targetTaskId))
      setSelectedVerifyTask(null)
      await verifyTask(targetTaskId, verifyNotes || 'Verified and approved by HR')
      setVerifyNotes('')
      await loadAll(true)
      window.dispatchEvent(new CustomEvent('mindful-metrics-refresh'))
    } catch (err) {
      alert(err.message || 'Could not verify task.')
      await loadAll(true)
    } finally {
      setBusy(false)
    }
  }

  async function handleRequestChanges() {
    if (!selectedVerifyTask || busy) return
    if (!changesNotes.trim()) {
      setChangesError('Please provide a meaningful explanation of the required revisions.')
      return
    }
    setChangesError('')
    setBusy(true)
    const targetTaskId = selectedVerifyTask.id
    try {
      // Optimistic removal from queue
      setVerificationQueue(prev => prev.filter(t => t.id !== targetTaskId && t.raw_id !== targetTaskId))
      setSelectedVerifyTask(null)
      await requestTaskChanges(targetTaskId, changesNotes.trim())
      setChangesNotes('')
      await loadAll(true)
      window.dispatchEvent(new CustomEvent('mindful-metrics-refresh'))
    } catch (err) {
      alert(err.message || 'Could not request task changes.')
      await loadAll(true)
    } finally {
      setBusy(false)
    }
  }


  const rawTasks = data?.tasks || []
  const summary = data?.summary || {
    assigned: rawTasks.length,
    completed: rawTasks.filter((t) => t.status === 'Completed').length,
    pending: rawTasks.filter((t) => ['In Progress', 'Pending', 'Not Started', 'Almost Completed'].includes(t.status)).length,
    blocked: rawTasks.filter((t) => t.status === 'Blocked').length,
    overdue: rawTasks.filter((t) => t.status === 'Overdue').length,
    completion_rate: `${Math.round((rawTasks.filter((t) => t.status === 'Completed').length / Math.max(rawTasks.length, 1)) * 100)}%`,
  }

  const pendingUnblocksCount = unblockRequests.filter(
    (r) => r.status === 'Pending HR Review' || r.status === 'More Information Required'
  ).length

  const awaitingVerifyCount = verificationQueue.filter(
    (t) => t.verification_status === 'Awaiting Verification'
  ).length

  const filteredTasks = useMemo(() => {
    return rawTasks.filter((t) => {
      const matchSearch =
        !searchQuery ||
        t.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        t.employee?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        t.id?.toLowerCase().includes(searchQuery.toLowerCase())

      const matchStatus =
        filterStatus === 'All' ||
        (filterStatus === 'In Progress' && ['In Progress', 'Pending', 'Almost Completed'].includes(t.status)) ||
        t.status?.toLowerCase() === filterStatus.toLowerCase()

      const matchPriority =
        filterPriority === 'All' || t.priority?.toLowerCase() === filterPriority.toLowerCase()

      const matchManager =
        filterManager === 'All' ||
        t.employee === filterManager ||
        t.employee_id === filterManager

      return matchSearch && matchStatus && matchPriority && matchManager
    })
  }, [rawTasks, searchQuery, filterStatus, filterPriority, filterManager])

  if (loading) return <LoadingSkeleton rows={4} />
  if (error && !data) return <ErrorState message={error} onRetry={loadAll} />

  const taskColumns = [
    {
      key: 'id',
      label: 'ID',
      render: (r) => <span className="font-mono text-xs font-semibold text-blue-600">{r.id}</span>,
    },
    {
      key: 'name',
      label: 'Task Title',
      render: (r) => (
        <div>
          <p className="font-semibold text-slate-900">{r.name}</p>
          {r.description && <p className="text-[11px] text-slate-400 truncate max-w-xs">{r.description}</p>}
        </div>
      ),
    },
    {
      key: 'employee',
      label: 'Assignee',
      render: (r) => (
        <div>
          <div className="flex items-center gap-1.5">
            <span className="font-medium text-slate-800">{r.employee}</span>
            <span
              className={`rounded px-1.5 py-0.2 text-[10px] font-semibold ${
                r.role === 'manager' ? 'bg-purple-100 text-purple-700' : 'bg-slate-100 text-slate-600'
              }`}
            >
              {r.role === 'manager' ? 'Manager' : 'Employee'}
            </span>
          </div>
          <p className="text-[11px] text-slate-400">
            {r.employee_id} · {r.department}
          </p>
        </div>
      ),
    },
    {
      key: 'priority',
      label: 'Priority',
      render: (r) => (
        <span
          className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold ${
            r.priority === 'High'
              ? 'bg-red-50 text-red-700'
              : r.priority === 'Low'
              ? 'bg-slate-100 text-slate-600'
              : 'bg-amber-50 text-amber-700'
          }`}
        >
          {r.priority}
        </span>
      ),
    },
    {
      key: 'progress',
      label: 'Progress',
      render: (r) => (
        <div className="flex items-center gap-2">
          <div className="h-1.5 w-16 overflow-hidden rounded-full bg-slate-100">
            <div
              className={`h-full rounded-full ${
                r.status === 'Completed'
                  ? 'bg-emerald-500'
                  : r.status === 'Blocked'
                  ? 'bg-red-500'
                  : r.status === 'Almost Completed'
                  ? 'bg-teal-500'
                  : 'bg-blue-600'
              }`}
              style={{ width: `${Math.min(100, Math.max(0, r.progress || 0))}%` }}
            />
          </div>
          <span className="text-xs text-slate-600">{r.progress || 0}%</span>
        </div>
      ),
    },
    {
      key: 'status',
      label: 'Status',
      render: (r) => <StatusBadge status={r.status} />,
    },
    {
      key: 'verification_status',
      label: 'Verification',
      render: (r) =>
        r.status === 'Completed' || (r.verification_status && r.verification_status !== 'None') ? (
          <StatusBadge status={r.verification_status || 'Awaiting Verification'} />
        ) : (
          <span className="text-slate-400">—</span>
        ),
    },
    {
      key: 'deadline',
      label: 'Deadline',
      render: (r) => <span className="text-xs text-slate-600">{r.deadline || 'Upcoming'}</span>,
    },
    {
      key: 'actions',
      label: '',
      render: (r) => (
        <button
          type="button"
          onClick={() => setSelectedTask(r)}
          className="btn-secondary text-xs flex items-center gap-1 py-1 px-2.5"
        >
          <Eye size={12} />
          <span>Details</span>
        </button>
      ),
    },
  ]

  const unblockColumns = [
    {
      key: 'task_id',
      label: 'Task',
      render: (r) => (
        <div>
          <span className="font-mono text-xs font-semibold text-blue-600">{r.task_id}</span>
          <p className="font-medium text-slate-800 text-xs">{r.task_title}</p>
        </div>
      ),
    },
    {
      key: 'requester_name',
      label: 'Requester',
      render: (r) => (
        <div>
          <span className="font-medium text-slate-800">{r.requester_name}</span>
          <p className="text-[11px] text-slate-400">
            {r.requester_id} · {r.department} ({r.requester_role})
          </p>
        </div>
      ),
    },
    {
      key: 'original_deadline',
      label: 'Original Deadline',
      render: (r) => <span className="text-xs text-slate-600">{r.original_deadline}</span>,
    },
    {
      key: 'requested_new_deadline',
      label: 'Requested Deadline',
      render: (r) => <span className="text-xs font-semibold text-blue-600">{r.requested_new_deadline}</span>,
    },
    {
      key: 'blocking_reason',
      label: 'Block Reason',
      render: (r) => <span className="text-xs text-red-600 max-w-xs truncate block">{r.blocking_reason}</span>,
    },
    {
      key: 'status',
      label: 'Status',
      render: (r) => <StatusBadge status={r.status} />,
    },
    {
      key: 'actions',
      label: 'Action',
      render: (r) => (
        <button
          type="button"
          onClick={() => {
            setSelectedUnblock(r)
            setUnblockDecisionReason('Approved deadline extension')
            setClarifyMessage('')
            setClarifyError('')
          }}
          className="btn-primary text-xs py-1 px-2.5"
        >
          Review
        </button>
      ),
    },
  ]

  const verifyColumns = [
    {
      key: 'id',
      label: 'Task',
      render: (r) => (
        <div>
          <span className="font-mono text-xs font-semibold text-blue-600">{r.id}</span>
          <p className="font-medium text-slate-800 text-xs">{r.title}</p>
        </div>
      ),
    },
    {
      key: 'employee_name',
      label: 'Assignee',
      render: (r) => (
        <div>
          <span className="font-medium text-slate-800">{r.employee_name}</span>
          <p className="text-[11px] text-slate-400">
            {r.employee_code} · {r.department} ({r.employee_role})
          </p>
        </div>
      ),
    },
    {
      key: 'completed_at',
      label: 'Completed At',
      render: (r) => <span className="text-xs text-slate-600">{r.completed_at}</span>,
    },
    {
      key: 'progress',
      label: 'Progress',
      render: () => <span className="text-xs font-semibold text-emerald-600">100% (Completed)</span>,
    },
    {
      key: 'verification_status',
      label: 'Verification Status',
      render: (r) => <StatusBadge status={r.verification_status} />,
    },
    {
      key: 'actions',
      label: 'Action',
      render: (r) => (
        <button
          type="button"
          onClick={() => {
            setSelectedVerifyTask(r)
            setVerifyNotes('')
            setChangesNotes('')
            setChangesError('')
          }}
          className="btn-primary text-xs py-1 px-2.5"
        >
          Verify Task
        </button>
      ),
    },
  ]

  return (
    <div className="page-stack fade-in">
      {/* 1. Summary KPI Cards */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
        <StatCard label="Total Tasks" value={summary.assigned} />
        <StatCard label="Completed" value={summary.completed} tone="low" />
        <StatCard label="In Progress" value={summary.pending} tone="mod" />
        <StatCard label="Blocked / Overdue" value={summary.blocked + (summary.overdue || 0)} tone="high" />
        <StatCard label="Completion Rate" value={summary.completion_rate} tone="blue" />
      </div>

      {/* 2. Navigation Tabs & Header */}
      <div className="card p-4 space-y-3">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b border-slate-100 pb-3">
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => setActiveTab('all_tasks')}
              className={`rounded-xl px-3 py-1.5 text-xs font-semibold transition ${
                activeTab === 'all_tasks'
                  ? 'bg-blue-600 text-white shadow-xs'
                  : 'bg-slate-100 text-slate-600 hover:text-slate-900'
              }`}
            >
              All Organizational Tasks ({filteredTasks.length})
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('unblock_requests')}
              className={`rounded-xl px-3 py-1.5 text-xs font-semibold transition flex items-center gap-1.5 ${
                activeTab === 'unblock_requests'
                  ? 'bg-blue-600 text-white shadow-xs'
                  : 'bg-slate-100 text-slate-600 hover:text-slate-900'
              }`}
            >
              <span>Unblock Requests</span>
              {pendingUnblocksCount > 0 && (
                <span className="rounded-full bg-amber-500 text-white px-1.5 py-0.2 text-[10px] font-bold">
                  {pendingUnblocksCount}
                </span>
              )}
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('verification_queue')}
              className={`rounded-xl px-3 py-1.5 text-xs font-semibold transition flex items-center gap-1.5 ${
                activeTab === 'verification_queue'
                  ? 'bg-blue-600 text-white shadow-xs'
                  : 'bg-slate-100 text-slate-600 hover:text-slate-900'
              }`}
            >
              <span>Verification Queue</span>
              {awaitingVerifyCount > 0 && (
                <span className="rounded-full bg-emerald-600 text-white px-1.5 py-0.2 text-[10px] font-bold">
                  {awaitingVerifyCount}
                </span>
              )}
            </button>
          </div>

          {activeTab === 'all_tasks' && (
            <button
              type="button"
              onClick={() => setOpenCreate(true)}
              className="btn-primary flex items-center gap-1.5 text-xs whitespace-nowrap self-start sm:self-auto"
            >
              <Plus size={14} />
              <span>Assign Task to Manager</span>
            </button>
          )}
        </div>

        {/* Filters (Active only for All Tasks tab) */}
        {activeTab === 'all_tasks' && (
          <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 md:grid-cols-4 pt-1">
            <div className="relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search title, manager, ID..."
                className="ww-input pl-8 text-xs"
              />
            </div>

            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="ww-input text-xs"
            >
              <option value="All">All Statuses</option>
              <option value="In Progress">In Progress</option>
              <option value="Almost Completed">Almost Completed</option>
              <option value="Completed">Completed</option>
              <option value="Blocked">Blocked</option>
              <option value="Not Started">Not Started</option>
              <option value="Overdue">Overdue</option>
            </select>

            <select
              value={filterPriority}
              onChange={(e) => setFilterPriority(e.target.value)}
              className="ww-input text-xs"
            >
              <option value="All">All Priorities</option>
              <option value="High">High Priority</option>
              <option value="Medium">Medium Priority</option>
              <option value="Low">Low Priority</option>
            </select>

            <select
              value={filterManager}
              onChange={(e) => setFilterManager(e.target.value)}
              className="ww-input text-xs"
            >
              <option value="All">All Assignees</option>
              {managers.map((m) => (
                <option key={m.id || m.employee_id} value={m.name}>
                  {m.name} ({m.department})
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* 3. Main Data Tables per Tab */}
      <div className="card p-4">
        {activeTab === 'all_tasks' && (
          filteredTasks.length === 0 ? (
            <div className="p-8 text-center">
              <div className="mx-auto mb-2 flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 text-slate-400">
                <ListChecks size={20} />
              </div>
              <p className="text-sm font-semibold text-slate-700">No tasks found</p>
              <p className="text-xs text-slate-400 mt-0.5">No tasks match your current filter criteria.</p>
            </div>
          ) : (
            <DataTable columns={taskColumns} rows={filteredTasks} />
          )
        )}

        {activeTab === 'unblock_requests' && (
          unblockRequests.length === 0 ? (
            <div className="p-8 text-center">
              <div className="mx-auto mb-2 flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 text-slate-400">
                <CheckCircle2 size={20} />
              </div>
              <p className="text-sm font-semibold text-slate-700">No unblock requests</p>
              <p className="text-xs text-slate-400 mt-0.5">There are no blocked tasks with pending HR unblock requests.</p>
            </div>
          ) : (
            <DataTable columns={unblockColumns} rows={unblockRequests} />
          )
        )}

        {activeTab === 'verification_queue' && (
          verificationQueue.length === 0 ? (
            <div className="p-8 text-center">
              <div className="mx-auto mb-2 flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 text-slate-400">
                <ShieldCheck size={20} />
              </div>
              <p className="text-sm font-semibold text-slate-700">Verification queue is clear</p>
              <p className="text-xs text-slate-400 mt-0.5">All completed tasks have been verified by HR.</p>
            </div>
          ) : (
            <DataTable columns={verifyColumns} rows={verificationQueue} />
          )
        )}
      </div>

      {/* 4. Assign Task to Manager Modal */}
      <Modal
        open={openCreate}
        title="Assign Organizational Task to Manager"
        onClose={() => setOpenCreate(false)}
        footer={
          <>
            <button type="button" onClick={() => setOpenCreate(false)} className="btn-secondary text-xs">
              Cancel
            </button>
            <button
              type="button"
              disabled={busy || !form.name.trim() || !form.assigned_to}
              className="btn-primary text-xs disabled:opacity-50"
              onClick={handleAssignTask}
            >
              {busy ? 'Assigning...' : 'Assign to Manager'}
            </button>
          </>
        }
      >
        <div className="space-y-3 text-xs">
          <label className="block text-slate-700 font-medium">
            Task Title <span className="text-red-500">*</span>
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="e.g. Conduct Q3 Engineering Workload Assessment"
              className="ww-input mt-1"
            />
          </label>

          <label className="block text-slate-700 font-medium">
            Assign to Department Manager <span className="text-red-500">*</span>
            <select
              value={form.assigned_to}
              onChange={(e) => setForm({ ...form, assigned_to: e.target.value })}
              className="ww-input mt-1"
            >
              {managers.map((m) => (
                <option key={m.id || m.employee_id} value={m.id || m.employee_id}>
                  {m.name} ({m.employee_id || `M${m.id}`}) — {m.department}
                </option>
              ))}
            </select>
          </label>

          <div className="grid grid-cols-2 gap-3">
            <label className="block text-slate-700 font-medium">
              Priority
              <select
                value={form.priority}
                onChange={(e) => setForm({ ...form, priority: e.target.value })}
                className="ww-input mt-1"
              >
                <option>High</option>
                <option>Medium</option>
                <option>Low</option>
              </select>
            </label>

            <label className="block text-slate-700 font-medium">
              Deadline Target
              <input
                type="text"
                value={form.deadline}
                onChange={(e) => setForm({ ...form, deadline: e.target.value })}
                placeholder="e.g. 25 Oct, End of Month"
                className="ww-input mt-1"
              />
            </label>
          </div>

          <label className="block text-slate-700 font-medium">
            Task Description & Deliverables
            <textarea
              rows={3}
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="Provide strategic deliverables, expectations, and review schedule..."
              className="ww-input mt-1"
            />
          </label>
        </div>
      </Modal>

      {/* 5. Task Details Modal */}
      <Modal
        open={Boolean(selectedTask)}
        title={selectedTask ? `${selectedTask.id}: ${selectedTask.name}` : 'Task Details'}
        onClose={() => setSelectedTask(null)}
        footer={
          <button type="button" onClick={() => setSelectedTask(null)} className="btn-secondary text-xs">
            Close
          </button>
        }
      >
        {selectedTask && (
          <div className="space-y-3.5 text-xs">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-2.5">
              <div>
                <span className="font-semibold text-slate-900 text-sm">{selectedTask.name}</span>
                <p className="text-slate-500 mt-0.5">
                  Assigned to: <strong className="text-slate-800">{selectedTask.employee}</strong> ({selectedTask.employee_id} · {selectedTask.department})
                </p>
              </div>
              <div className="flex items-center gap-2">
                <StatusBadge status={selectedTask.status} />
                <span className="font-semibold text-blue-600">{selectedTask.progress}% Complete</span>
              </div>
            </div>

            {selectedTask.description && (
              <div>
                <span className="font-semibold text-slate-600">Description:</span>
                <p className="mt-1 text-slate-800 bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                  {selectedTask.description}
                </p>
              </div>
            )}

            <div className="grid grid-cols-2 gap-3 bg-slate-50 p-3 rounded-lg border border-slate-100">
              <div>
                <span className="text-slate-400">Priority:</span>
                <p className="font-semibold text-slate-800">{selectedTask.priority}</p>
              </div>
              <div>
                <span className="text-slate-400">Deadline:</span>
                <p className="font-semibold text-slate-800">{selectedTask.deadline || 'Upcoming'}</p>
              </div>
              <div>
                <span className="text-slate-400">Assigned By:</span>
                <p className="font-semibold text-slate-800">{selectedTask.assigned_by || 'HR Team'}</p>
              </div>
              <div>
                <span className="text-slate-400">Created:</span>
                <p className="font-semibold text-slate-800">{selectedTask.created_at || '—'}</p>
              </div>
            </div>

            {selectedTask.blocked_reason && selectedTask.blocked_reason !== '—' && (
              <div className="rounded-lg bg-red-50 p-3 border border-red-200 text-red-800">
                <span className="font-bold">Active Blocker Reported:</span>
                <p className="mt-0.5">{selectedTask.blocked_reason}</p>
              </div>
            )}

            {selectedTask.work_update && selectedTask.work_update !== '—' && (
              <div className="rounded-lg bg-blue-50 p-3 border border-blue-200 text-blue-900">
                <span className="font-bold">Latest Work Progress Update:</span>
                <p className="mt-0.5">{selectedTask.work_update}</p>
              </div>
            )}
          </div>
        )}
      </Modal>

      {/* 6. HR Unblock Request Review Modal */}
      <Modal
        open={Boolean(selectedUnblock)}
        maxWidth="max-w-xl"
        title={selectedUnblock ? `Review Unblock Request: ${selectedUnblock.task_title}` : 'Review Unblock'}
        onClose={() => setSelectedUnblock(null)}
        footer={
          <div className="flex flex-wrap items-center justify-between gap-2 w-full">
            <button type="button" onClick={() => setSelectedUnblock(null)} className="btn-secondary text-xs">
              Cancel
            </button>
            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled={busy}
                className="btn-secondary text-xs text-red-600 border-red-200 hover:bg-red-50"
                onClick={handleRejectUnblock}
              >
                Reject Request
              </button>
              <button
                type="button"
                disabled={busy}
                className="btn-secondary text-xs text-amber-700 border-amber-300 hover:bg-amber-50"
                onClick={handleClarifyUnblock}
              >
                Ask for Details
              </button>
              <button
                type="button"
                disabled={busy}
                className="btn-primary text-xs"
                onClick={handleApproveUnblock}
              >
                Approve & Unblock
              </button>
            </div>
          </div>
        }
      >
        {selectedUnblock && (
          <div className="space-y-3.5 text-xs">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
              <div>
                <p className="font-semibold text-slate-800 text-sm">{selectedUnblock.task_title}</p>
                <p className="text-slate-500">
                  Requester: <strong>{selectedUnblock.requester_name}</strong> ({selectedUnblock.requester_id} · {selectedUnblock.department})
                </p>
              </div>
              <StatusBadge status={selectedUnblock.status} />
            </div>

            <div className="grid grid-cols-2 gap-3 bg-slate-50 p-3 rounded-lg border border-slate-100">
              <div>
                <span className="text-slate-400">Original Deadline:</span>
                <p className="font-semibold text-slate-800">{selectedUnblock.original_deadline}</p>
              </div>
              <div>
                <span className="text-slate-400">Requested Extension:</span>
                <p className="font-semibold text-blue-600">{selectedUnblock.requested_new_deadline}</p>
              </div>
            </div>

            <div className="rounded-lg bg-red-50 p-3 border border-red-200 text-red-900">
              <span className="font-bold">Blocking Reason:</span>
              <p className="mt-0.5">{selectedUnblock.blocking_reason}</p>
            </div>

            <div>
              <span className="font-semibold text-slate-700">Reason for Extension:</span>
              <p className="mt-1 text-slate-800 bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                {selectedUnblock.extension_reason}
              </p>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <span className="font-semibold text-slate-700">Work Completed So Far:</span>
                <p className="mt-1 text-slate-800 bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                  {selectedUnblock.work_completed}
                </p>
              </div>
              <div>
                <span className="font-semibold text-slate-700">Remaining Work:</span>
                <p className="mt-1 text-slate-800 bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                  {selectedUnblock.remaining_work}
                </p>
              </div>
            </div>

            {selectedUnblock.clarification_response && (
              <div className="rounded-lg bg-blue-50 p-3 border border-blue-200 text-blue-900">
                <span className="font-bold">Requester Clarification Response:</span>
                <p className="mt-0.5">{selectedUnblock.clarification_response}</p>
              </div>
            )}

            <div className="border-t border-slate-100 pt-3 space-y-2">
              <label className="block text-slate-700 font-medium">
                Decision Notes / Approval Reason
                <input
                  type="text"
                  value={unblockDecisionReason}
                  onChange={(e) => setUnblockDecisionReason(e.target.value)}
                  placeholder="e.g. Approved extension to 25 Oct"
                  className="ww-input mt-1"
                />
              </label>

              <label className="block text-slate-700 font-medium">
                Clarification Request (fill this if asking for more information)
                <textarea
                  rows={2}
                  value={clarifyMessage}
                  onChange={(e) => {
                    setClarifyMessage(e.target.value)
                    if (clarifyError) setClarifyError('')
                  }}
                  placeholder="Explain what additional details are needed from the requester..."
                  className={`ww-input mt-1 ${clarifyError ? 'border-rose-400 focus:border-rose-500 ring-1 ring-rose-200' : ''}`}
                />
                {clarifyError && (
                  <p className="mt-1 text-xs text-rose-600 font-medium">{clarifyError}</p>
                )}
              </label>
            </div>
          </div>
        )}
      </Modal>

      {/* 7. HR Task Verification Modal */}
      <Modal
        open={Boolean(selectedVerifyTask)}
        maxWidth="max-w-xl"
        title={selectedVerifyTask ? `Verify Completed Task: ${selectedVerifyTask.title}` : 'Verify Task'}
        onClose={() => setSelectedVerifyTask(null)}
        footer={
          <div className="flex flex-wrap items-center justify-between gap-2 w-full">
            <button type="button" onClick={() => setSelectedVerifyTask(null)} className="btn-secondary text-xs">
              Cancel
            </button>
            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled={busy}
                className="btn-secondary text-xs text-amber-700 border-amber-300 hover:bg-amber-50"
                onClick={handleRequestChanges}
              >
                Request Changes
              </button>
              <button
                type="button"
                disabled={busy}
                className="btn-primary text-xs"
                onClick={handleVerifyTask}
              >
                Verify & Sign Off
              </button>
            </div>
          </div>
        }
      >
        {selectedVerifyTask && (
          <div className="space-y-3.5 text-xs">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
              <div>
                <p className="font-semibold text-slate-800 text-sm">{selectedVerifyTask.title}</p>
                <p className="text-slate-500">
                  Owner: <strong>{selectedVerifyTask.employee_name}</strong> ({selectedVerifyTask.employee_code} · {selectedVerifyTask.department})
                </p>
              </div>
              <div className="flex items-center gap-1.5">
                <StatusBadge status="Completed" />
                <StatusBadge status={selectedVerifyTask.verification_status} />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 bg-slate-50 p-3 rounded-lg border border-slate-100">
              <div>
                <span className="text-slate-400">Completed At:</span>
                <p className="font-semibold text-slate-800">{selectedVerifyTask.completed_at}</p>
              </div>
              <div>
                <span className="text-slate-400">Final Progress:</span>
                <p className="font-semibold text-emerald-600">100%</p>
              </div>
            </div>

            <div>
              <span className="font-semibold text-slate-700">Deliverables / Final Work Update:</span>
              <p className="mt-1 text-slate-800 bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                {selectedVerifyTask.work_update || 'No notes provided upon completion.'}
              </p>
            </div>

            <div className="border-t border-slate-100 pt-3 space-y-2">
              <label className="block text-slate-700 font-medium">
                Verification Sign-off Notes (Optional)
                <input
                  type="text"
                  value={verifyNotes}
                  onChange={(e) => setVerifyNotes(e.target.value)}
                  placeholder="e.g. Verified deliverables and code review completed"
                  className="ww-input mt-1"
                />
              </label>

              <label className="block text-slate-700 font-medium">
                Request Revisions (fill this if requesting changes)
                <textarea
                  rows={2}
                  value={changesNotes}
                  onChange={(e) => {
                    setChangesNotes(e.target.value)
                    if (changesError) setChangesError('')
                  }}
                  placeholder="Explain required improvements before signing off..."
                  className={`ww-input mt-1 ${changesError ? 'border-rose-400 focus:border-rose-500 ring-1 ring-rose-200' : ''}`}
                />
                {changesError && (
                  <p className="mt-1 text-xs text-rose-600 font-medium">{changesError}</p>
                )}
              </label>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}
