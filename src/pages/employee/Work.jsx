import { useEffect, useState } from 'react'
import StatCard from '../../components/common/StatCard'
import DataTable from '../../components/common/DataTable'
import StatusBadge from '../../components/common/StatusBadge'
import ChartCard from '../../components/common/ChartCard'
import Modal from '../../components/common/Modal'
import { Pie, PieChart, Cell, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts'
import { getWorkData, updateTaskDetails, submitTaskUnblockRequest, replyTaskUnblockClarification } from '../../services/api'
import LoadingSkeleton from '../../components/common/LoadingSkeleton'
import ErrorState from '../../components/common/ErrorState'

function deriveStatusFromProgress(p) {
  const val = Number(p) || 0
  if (val <= 0) return 'Not Started'
  if (val <= 75) return 'In Progress'
  if (val <= 99) return 'Almost Completed'
  return 'Completed'
}

export default function Work() {
  const [data, setData] = useState(null)
  const [rows, setRows] = useState([])
  const [error, setError] = useState('')
  const [openEdit, setOpenEdit] = useState(false)
  const [selectedTask, setSelectedTask] = useState(null)
  const [busy, setBusy] = useState(false)

  // Edit Task Form
  const [editForm, setEditForm] = useState({
    progress: 50,
    work_update: '',
  })

  // Unblock Request Modal state
  const [openUnblock, setOpenUnblock] = useState(false)
  const [unblockTask, setUnblockTask] = useState(null)
  const [unblockForm, setUnblockForm] = useState({
    requested_new_deadline: '',
    extension_reason: '',
    work_completed: '',
    remaining_work: '',
    supporting_notes: '',
  })
  const [clarifyReply, setClarifyReply] = useState('')

  useEffect(() => {
    loadWork()
  }, [])

  async function loadWork() {
    try {
      const d = await getWorkData()
      setData(d)
      setRows(d.tasks || [])
    } catch {
      setError('Work data could not be loaded.')
    }
  }

  function handleRowClick(row) {
    setSelectedTask(row)
    setEditForm({
      progress: row.progress !== undefined ? row.progress : (row.status === 'Completed' ? 100 : 50),
      work_update: row.work_update || '',
    })
    setOpenEdit(true)
  }

  async function handleUpdateTask(e) {
    if (e && e.preventDefault) e.preventDefault()
    if (!selectedTask || busy) return
    if (selectedTask.verification_status !== 'Changes Requested' && (selectedTask.is_locked || selectedTask.status === 'Completed')) {
      alert('Completed tasks are locked against ordinary updates.')
      return
    }
    if (selectedTask.status === 'Blocked') {
      alert('This task is blocked. Please submit an unblock request.')
      return
    }

    setBusy(true)
    const targetTaskId = selectedTask.raw_id || selectedTask.id
    const newProgress = Number(editForm.progress)
    const newUpdate = editForm.work_update

    try {
      await updateTaskDetails(targetTaskId, {
        progress: newProgress,
        work_update: newUpdate,
      })

      // Update rows upon confirmed save
      setRows(prev => prev.map(t => {
        if (t.id === targetTaskId || t.raw_id === targetTaskId || t.id === `T-${targetTaskId}`) {
          return {
            ...t,
            progress: newProgress,
            completion_percentage: newProgress,
            work_update: newUpdate,
            status: newProgress === 100 ? 'Completed' : (newProgress > 75 ? 'Almost Completed' : (newProgress > 0 ? 'In Progress' : 'Not Started'))
          }
        }
        return t
      }))

      setOpenEdit(false)
      setSelectedTask(null)
      await loadWork()
      window.dispatchEvent(new CustomEvent('mindful-metrics-refresh'))
    } catch (err) {
      alert(err.message || 'Could not update task.')
    } finally {
      setBusy(false)
    }
  }

  function handleOpenUnblockModal(task) {
    setUnblockTask(task)
    const existingReq = task.active_unblock_request
    setUnblockForm({
      requested_new_deadline: existingReq?.requested_new_deadline || '',
      extension_reason: existingReq?.extension_reason || '',
      work_completed: existingReq?.work_completed || '',
      remaining_work: existingReq?.remaining_work || '',
      supporting_notes: existingReq?.supporting_notes || '',
    })
    setClarifyReply('')
    setOpenUnblock(true)
  }

  async function handleSubmitUnblock(e) {
    e.preventDefault()
    if (!unblockTask || busy) return
    if (!unblockForm.requested_new_deadline.trim()) {
      alert('Please enter a requested new deadline.')
      return
    }
    if (!unblockForm.extension_reason.trim()) {
      alert('Please provide a reason for the extension.')
      return
    }
    if (!unblockForm.work_completed.trim() || !unblockForm.remaining_work.trim()) {
      alert('Please document work completed so far and remaining deliverables.')
      return
    }

    setBusy(true)
    try {
      await submitTaskUnblockRequest(unblockTask.id, unblockForm)
      setOpenUnblock(false)
      setUnblockTask(null)
      await loadWork()
      window.dispatchEvent(new CustomEvent('mindful-metrics-refresh'))
    } catch (err) {
      alert(err.message || 'Could not submit unblock request.')
    } finally {
      setBusy(false)
    }
  }

  async function handleReplyClarification(e) {
    e.preventDefault()
    if (!unblockTask?.active_unblock_request?.id || !clarifyReply.trim() || busy) return
    setBusy(true)
    try {
      await replyTaskUnblockClarification(unblockTask.active_unblock_request.id, clarifyReply.trim())
      setOpenUnblock(false)
      setUnblockTask(null)
      await loadWork()
      window.dispatchEvent(new CustomEvent('mindful-metrics-refresh'))
    } catch (err) {
      alert(err.message || 'Could not submit clarification response.')
    } finally {
      setBusy(false)
    }
  }

  if (error) return <ErrorState message={error} onRetry={() => window.location.reload()} />
  if (!data) return <LoadingSkeleton rows={2} />

  const pieSlices = [
    { name: 'Completed', value: data?.summary?.completed || 0, fill: '#22c55e' },
    { name: 'Almost Done', value: data?.summary?.almost_completed || 0, fill: '#10b981' },
    { name: 'In Progress', value: data?.summary?.in_progress || 0, fill: '#3b82f6' },
    { name: 'Not Started', value: data?.summary?.not_started || 0, fill: '#94a3b8' },
    { name: 'Blocked', value: data?.summary?.blocked || 0, fill: '#ef4444' },
  ].filter((p) => p.value > 0)

  const pie = pieSlices.length > 0 ? pieSlices : [{ name: 'No Tasks', value: 1, fill: '#e2e8f0' }]

  const statusBars = [
    { n: 'Done', v: data?.summary?.completed || 0 },
    { n: 'Almost', v: data?.summary?.almost_completed || 0 },
    { n: 'Progress', v: data?.summary?.in_progress || 0 },
    { n: 'Pending', v: data?.summary?.not_started || 0 },
    { n: 'Blocked', v: data?.summary?.blocked || 0 },
  ]

  const derivedEditStatus = deriveStatusFromProgress(editForm.progress)
  const isSelectedLocked =
    (selectedTask?.is_locked || selectedTask?.status === 'Completed') &&
    selectedTask?.verification_status !== 'Changes Requested'
  const isSelectedBlocked = selectedTask?.is_blocked || selectedTask?.status === 'Blocked'

  return (
    <div className="page-stack fade-in">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
        <StatCard label="Tasks Assigned" value={data.summary.assigned} />
        <StatCard label="Completed" value={data.summary.completed} tone="low" />
        <StatCard label="Pending" value={data.summary.pending} tone="mod" />
        <StatCard label="Blocked / Overdue" value={data.summary.blocked || data.summary.overdue || 0} tone="high" />
        <StatCard label="Completion" value={`${data.summary.completion}%`} tone="blue" />
      </div>

      <div className="grid gap-3 lg:grid-cols-3">
        <ChartCard title="Task Completion">
          <div className="flex h-full min-w-0 flex-col">
            <div className="relative min-h-0 flex-1">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={pie} dataKey="value" innerRadius={45} outerRadius={70}>
                    {pie.map((p) => (
                      <Cell key={p.name} fill={p.fill} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
              {/* Centered Total Assigned Count in Donut */}
              <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-xl font-bold text-slate-800 leading-none">
                  {data?.summary?.assigned ?? rows.length}
                </span>
                <span className="text-[10px] uppercase tracking-wider text-slate-400 font-medium mt-0.5">
                  Total
                </span>
              </div>
            </div>
            <div className="flex shrink-0 flex-wrap justify-center gap-x-3 gap-y-1 pt-1 text-[11px] text-[#6B7C93]">
              {pie.map((p) => (
                <span key={p.name} className="inline-flex items-center gap-1 whitespace-nowrap">
                  <span className="h-2 w-2 rounded-full" style={{ backgroundColor: p.fill }} />
                  {p.name} {data.summary.assigned ? `${Math.round((p.value / data.summary.assigned) * 100)}%` : '0%'}
                </span>
              ))}
            </div>
          </div>
        </ChartCard>
        <ChartCard title="Weekly Workload Hours">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data?.hoursWeek?.length ? data.hoursWeek : []}>
              <CartesianGrid stroke="#eef2f7" vertical={false} />
              <XAxis dataKey="d" tick={{ fontSize: 11 }} />
              <YAxis width={24} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="v" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Status Breakdown">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={statusBars}>
              <CartesianGrid stroke="#eef2f7" vertical={false} />
              <XAxis dataKey="n" tick={{ fontSize: 11 }} />
              <YAxis width={24} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="v" fill="#60a5fa" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <div className="card p-4">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-800">Assigned Tasks ({rows.length})</h3>
          {/* Add Task button removed for Employee/Manager My Work page as requested */}
        </div>
        <DataTable
          onRowClick={handleRowClick}
          columns={[
            {
              key: 'name',
              label: 'Task',
              render: (r) => (
                <div>
                  <p className="font-semibold text-slate-900">{r.name}</p>
                  {r.description && <p className="text-[11px] text-slate-400 truncate max-w-xs">{r.description}</p>}
                </div>
              ),
            },
            { key: 'priority', label: 'Priority' },
            { key: 'deadline', label: 'Deadline' },
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
                      style={{ width: `${Math.min(100, Math.max(0, r.progress !== undefined ? r.progress : 0))}%` }}
                    />
                  </div>
                  <span className="text-xs text-slate-600">{r.progress !== undefined ? r.progress : 0}%</span>
                </div>
              ),
            },
            { key: 'status', label: 'Status', render: (r) => <StatusBadge status={r.status} /> },
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
              key: 'actions',
              label: 'Actions',
              render: (r) => {
                if (r.status === 'Blocked') {
                  const activeReq = r.active_unblock_request
                  if (activeReq) {
                    return (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation()
                          handleOpenUnblockModal(r)
                        }}
                        className={`text-[11px] font-medium px-2 py-0.5 rounded border transition ${
                          activeReq.status === 'More Information Required'
                            ? 'bg-blue-50 text-blue-700 border-blue-200 hover:bg-blue-100'
                            : 'bg-amber-50 text-amber-700 border-amber-200 hover:bg-amber-100'
                        }`}
                      >
                        {activeReq.status === 'More Information Required' ? 'Reply to HR' : activeReq.status}
                      </button>
                    )
                  }
                  return (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation()
                        handleOpenUnblockModal(r)
                      }}
                      className="btn-secondary py-0.5 px-2 text-[11px] text-red-600 border-red-200 hover:bg-red-50"
                    >
                      Request Unblock
                    </button>
                  )
                }
                return null
              },
            },
          ]}
          rows={rows}
        />
        <p className="mt-2 text-xs text-slate-400">
          Click any row to update task progress (0–100%) or add work updates. Status is automatically determined by progress.
        </p>
      </div>

      {/* Edit Task Modal */}
      <Modal
        open={openEdit}
        title={selectedTask ? `Update Task: ${selectedTask.name}` : 'Update Task'}
        onClose={() => setOpenEdit(false)}
        footer={
          <>
            <button type="button" onClick={() => setOpenEdit(false)} className="btn-secondary">
              Cancel
            </button>
            <button
              type="button"
              disabled={busy || isSelectedLocked || isSelectedBlocked}
              className="btn-primary disabled:opacity-50"
              onClick={handleUpdateTask}
            >
              {busy ? 'Saving...' : 'Save Update'}
            </button>
          </>
        }
      >
        <div className="space-y-3">
          {/* Changes Requested Alert */}
          {selectedTask?.verification_status === 'Changes Requested' && (
            <div className="rounded-lg bg-amber-50 border border-amber-300 p-3 text-xs text-amber-900">
              <p className="font-semibold flex items-center gap-1.5 text-amber-800">
                <span className="h-2 w-2 rounded-full bg-amber-500 animate-pulse" />
                HR Requested Changes on this Task
              </p>
              <div className="mt-1.5 text-amber-900 bg-white/80 p-2.5 rounded border border-amber-200">
                <strong>HR Feedback:</strong> {selectedTask.verification_notes || 'Please revise your deliverables and resubmit.'}
              </div>
              <p className="mt-1.5 text-[11px] text-amber-700">
                Apply the requested corrections below, update your work summary, and set progress to 100% to resubmit for verification.
              </p>
            </div>
          )}

          {/* Locked / Blocked Alerts */}
          {isSelectedLocked && (
            <div className="rounded-lg bg-emerald-50 border border-emerald-200 p-3 text-xs text-emerald-800">
              <p className="font-semibold">Task Completed (100%)</p>
              <p className="mt-0.5 text-emerald-700">
                This task is locked against further ordinary progress updates. Verification Status:{' '}
                <span className="font-semibold">{selectedTask.verification_status || 'Awaiting Verification'}</span>.
              </p>
              {selectedTask.verification_notes && (
                <p className="mt-1 text-[11px] text-emerald-600 italic">Notes: {selectedTask.verification_notes}</p>
              )}
            </div>
          )}

          {isSelectedBlocked && (
            <div className="rounded-lg bg-red-50 border border-red-200 p-3 text-xs text-red-800">
              <p className="font-semibold">Task Blocked</p>
              <p className="mt-0.5 text-red-700">
                {selectedTask.blocked_reason || 'This task missed its deadline or has dependencies.'} Ordinary progress
                updates are disabled.
              </p>
              <div className="mt-2">
                <button
                  type="button"
                  onClick={() => {
                    setOpenEdit(false)
                    handleOpenUnblockModal(selectedTask)
                  }}
                  className="btn-secondary py-1 px-2.5 text-xs text-red-700 border-red-300 hover:bg-red-100"
                >
                  {selectedTask.active_unblock_request ? 'View / Manage Unblock Request' : 'Submit Unblock Request to HR'}
                </button>
              </div>
            </div>
          )}

          {/* Automatic Status derived from Progress */}
          <div className="grid grid-cols-2 gap-3">
            <div className="text-sm">
              <span className="text-slate-600 font-medium">Automatic Status</span>
              <div className="mt-2 flex items-center gap-1.5">
                <StatusBadge status={isSelectedLocked ? 'Completed' : isSelectedBlocked ? 'Blocked' : derivedEditStatus} />
              </div>
            </div>

            <label className="text-sm">
              Progress: <span className="font-semibold text-blue-600">{editForm.progress}%</span>
              <input
                type="range"
                min="0"
                max="100"
                step="5"
                disabled={isSelectedLocked || isSelectedBlocked}
                value={editForm.progress}
                onChange={(e) => {
                  const p = Number(e.target.value)
                  setEditForm((prev) => ({
                    ...prev,
                    progress: p,
                  }))
                }}
                className="mt-2 w-full disabled:opacity-50"
              />
            </label>
          </div>

          <label className="block text-sm">
            Work Update (what did you work on or finish?)
            <textarea
              rows={2}
              disabled={isSelectedLocked || isSelectedBlocked}
              value={editForm.work_update}
              onChange={(e) => setEditForm((prev) => ({ ...prev, work_update: e.target.value }))}
              placeholder="e.g. Completed initial design, API integration in progress..."
              className="ww-input disabled:opacity-50"
            />
          </label>
        </div>
      </Modal>

      {/* Blocked Task Unblock Request Modal */}
      <Modal
        open={openUnblock}
        title={unblockTask ? `HR Unblock Request: ${unblockTask.name}` : 'Unblock Request'}
        onClose={() => setOpenUnblock(false)}
        footer={
          <>
            <button type="button" onClick={() => setOpenUnblock(false)} className="btn-secondary">
              Cancel
            </button>
            {unblockTask?.active_unblock_request?.status === 'More Information Required' ? (
              <button
                type="button"
                disabled={busy || !clarifyReply.trim()}
                className="btn-primary disabled:opacity-50"
                onClick={handleReplyClarification}
              >
                {busy ? 'Sending...' : 'Send Clarification Response'}
              </button>
            ) : (
              <button
                type="button"
                disabled={busy || unblockTask?.active_unblock_request?.status === 'Pending HR Review'}
                className="btn-primary disabled:opacity-50"
                onClick={handleSubmitUnblock}
              >
                {busy ? 'Submitting...' : 'Submit Request to HR'}
              </button>
            )}
          </>
        }
      >
        <div className="space-y-3 text-xs">
          {/* Active Request Alert */}
          {unblockTask?.active_unblock_request && (
            <div className="rounded-lg bg-slate-50 border border-slate-200 p-3">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-slate-800">Current Request Status</span>
                <StatusBadge status={unblockTask.active_unblock_request.status} />
              </div>
              {unblockTask.active_unblock_request.clarification_requested && (
                <div className="mt-2 p-2 rounded bg-amber-50 border border-amber-200 text-amber-900">
                  <p className="font-semibold text-[11px]">HR Clarification Request:</p>
                  <p className="mt-0.5">{unblockTask.active_unblock_request.clarification_requested}</p>
                </div>
              )}
            </div>
          )}

          {/* Reply field if clarification requested */}
          {unblockTask?.active_unblock_request?.status === 'More Information Required' ? (
            <label className="block text-slate-700 font-medium">
              Your Response to HR <span className="text-red-500">*</span>
              <textarea
                rows={3}
                value={clarifyReply}
                onChange={(e) => setClarifyReply(e.target.value)}
                placeholder="Provide the details requested by HR..."
                className="ww-input mt-1"
              />
            </label>
          ) : (
            <>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <span className="font-medium text-slate-600">Original Deadline</span>
                  <p className="font-semibold text-slate-800 mt-0.5">{unblockTask?.deadline || '—'}</p>
                </div>
                <label className="block text-slate-700 font-medium">
                  Requested New Deadline <span className="text-red-500">*</span>
                  <input
                    type="date"
                    value={unblockForm.requested_new_deadline}
                    onChange={(e) => setUnblockForm({ ...unblockForm, requested_new_deadline: e.target.value })}
                    className="ww-input mt-0.5"
                  />
                </label>
              </div>

              <label className="block text-slate-700 font-medium">
                Reason for Extension Request <span className="text-red-500">*</span>
                <textarea
                  rows={2}
                  value={unblockForm.extension_reason}
                  onChange={(e) => setUnblockForm({ ...unblockForm, extension_reason: e.target.value })}
                  placeholder="Explain why deadline was missed or why blocker requires an extension..."
                  className="ww-input mt-1"
                />
              </label>

              <div className="grid grid-cols-2 gap-3">
                <label className="block text-slate-700 font-medium">
                  Work Completed So Far <span className="text-red-500">*</span>
                  <textarea
                    rows={2}
                    value={unblockForm.work_completed}
                    onChange={(e) => setUnblockForm({ ...unblockForm, work_completed: e.target.value })}
                    placeholder="Deliverables completed..."
                    className="ww-input mt-1"
                  />
                </label>

                <label className="block text-slate-700 font-medium">
                  Remaining Work <span className="text-red-500">*</span>
                  <textarea
                    rows={2}
                    value={unblockForm.remaining_work}
                    onChange={(e) => setUnblockForm({ ...unblockForm, remaining_work: e.target.value })}
                    placeholder="Steps required to finish..."
                    className="ww-input mt-1"
                  />
                </label>
              </div>

              <label className="block text-slate-700 font-medium">
                Supporting Notes (Optional)
                <input
                  type="text"
                  value={unblockForm.supporting_notes}
                  onChange={(e) => setUnblockForm({ ...unblockForm, supporting_notes: e.target.value })}
                  placeholder="Any additional details for HR..."
                  className="ww-input mt-1"
                />
              </label>
            </>
          )}
        </div>
      </Modal>
    </div>
  )
}
