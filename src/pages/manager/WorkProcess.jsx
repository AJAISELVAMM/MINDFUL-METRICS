import { useEffect, useState } from 'react'
import StatCard from '../../components/common/StatCard'
import ChartCard from '../../components/common/ChartCard'
import DataTable from '../../components/common/DataTable'
import StatusBadge from '../../components/common/StatusBadge'
import Modal from '../../components/common/Modal'
import LoadingSkeleton from '../../components/common/LoadingSkeleton'
import ComparisonChart from '../../components/charts/ComparisonChart'
import WorkloadChart from '../../components/charts/WorkloadChart'
import { expectedActualToday, hoursWeek } from '../../data/chartData'
import { getTeamWorkload, createTask, getWorkData, updateTaskDetails } from '../../services/api'

export default function WorkProcess() {
  const [data, setData] = useState(null)
  const [myData, setMyData] = useState(null)
  const [activeTab, setActiveTab] = useState('team') // 'team' | 'my_tasks'
  const [loading, setLoading] = useState(true)
  const [openAssign, setOpenAssign] = useState(false)
  const [openUpdateMy, setOpenUpdateMy] = useState(false)
  const [selectedMyTask, setSelectedMyTask] = useState(null)
  const [busy, setBusy] = useState(false)

  // Manager assigning task to team member form
  const [form, setForm] = useState({
    name: '',
    employee_id: '',
    priority: 'Medium',
    deadline: 'Upcoming',
    description: '',
  })

  // Manager updating their own assigned task from HR
  const [updateForm, setUpdateForm] = useState({
    status: 'In Progress',
    progress: 50,
    work_update: '',
    blocked_reason: '',
  })

  useEffect(() => {
    loadData()
  }, [])

  async function loadData() {
    try {
      const [resTeam, resMy] = await Promise.all([
        getTeamWorkload().catch(() => null),
        getWorkData().catch(() => null),
      ])
      setData(resTeam)
      setMyData(resMy)
      if (resTeam?.members && resTeam.members.length > 0 && !form.employee_id) {
        setForm((f) => ({ ...f, employee_id: resTeam.members[0].id }))
      }
    } catch {
      // fallback handled gracefully
    } finally {
      setLoading(false)
    }
  }

  async function handleAssignTask(e) {
    e.preventDefault()
    if (!form.name.trim()) return
    if (busy) return
    setBusy(true)
    try {
      await createTask(form)
      setOpenAssign(false)
      setForm({
        name: '',
        employee_id: data?.members?.[0]?.id || '',
        priority: 'Medium',
        deadline: 'Upcoming',
        description: '',
      })
      await loadData()
      window.dispatchEvent(new CustomEvent('mindful-metrics-refresh'))
    } catch (err) {
      alert(err.message || 'Could not assign task.')
    } finally {
      setBusy(false)
    }
  }

  function deriveStatusFromProgress(p) {
    const val = Number(p) || 0
    if (val <= 0) return 'Not Started'
    if (val <= 75) return 'In Progress'
    if (val <= 99) return 'Almost Completed'
    return 'Completed'
  }

  function handleOpenUpdateMy(task) {
    setSelectedMyTask(task)
    setUpdateForm({
      progress: task.progress !== undefined ? task.progress : (task.status === 'Completed' ? 100 : 50),
      work_update: task.work_update || '',
      blocked_reason: task.blocked_reason || '',
    })
    setOpenUpdateMy(true)
  }

  async function handleSaveMyTaskUpdate(e) {
    if (e && e.preventDefault) e.preventDefault()
    if (!selectedMyTask || busy) return
    if (selectedMyTask.verification_status !== 'Changes Requested' && (selectedMyTask.status === 'Completed' || (selectedMyTask.progress === 100))) {
      alert('Completed tasks are locked against ordinary updates.')
      return
    }
    if (selectedMyTask.status === 'Blocked') {
      alert('This task is blocked. Please submit an unblock request to HR.')
      return
    }

    setBusy(true)
    const targetTaskId = selectedMyTask.raw_id || selectedMyTask.id
    const newProgress = Number(updateForm.progress)
    const newUpdate = updateForm.work_update

    try {
      await updateTaskDetails(targetTaskId, {
        progress: newProgress,
        work_update: newUpdate,
      })

      // Update state upon confirmed success
      setMyData(prev => ({
        ...prev,
        tasks: (prev?.tasks || []).map(t => {
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
        })
      }))

      setOpenUpdateMy(false)
      setSelectedMyTask(null)
      await loadData()
      window.dispatchEvent(new CustomEvent('mindful-metrics-refresh'))
    } catch (err) {
      alert(err.message || 'Could not update task.')
    } finally {
      setBusy(false)
    }
  }

  if (loading) return <LoadingSkeleton rows={3} />

  const summary = data?.summary || {
    assigned: 86,
    completion_rate: '71%',
    pending: 18,
    blocked: 4,
  }

  const tasks = data?.tasks || []
  const members = data?.members || []
  const myAssignedTasks = myData?.tasks || []

  return (
    <div className="page-stack fade-in">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatCard label="Task assignment" value={summary.assigned} />
        <StatCard label="Completion" value={summary.completion_rate || `${summary.completion}%`} tone="low" />
        <StatCard label="Pending" value={summary.pending} tone="mod" />
        <StatCard label="Blocked / Overdue" value={summary.blocked || summary.overdue || 0} tone="high" />
      </div>

      <div className="grid gap-3 lg:grid-cols-2">
        <ChartCard title="Working hours">
          <WorkloadChart data={hoursWeek} />
        </ChartCard>
        <ChartCard title="Expected vs actual workload">
          <ComparisonChart data={expectedActualToday} />
        </ChartCard>
      </div>

      <div className="card p-4">
        {/* Tab Switcher Header */}
        <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setActiveTab('team')}
              className={`rounded-xl px-3 py-1.5 text-xs font-semibold transition ${
                activeTab === 'team'
                  ? 'bg-blue-600 text-white shadow-xs'
                  : 'bg-slate-100 text-slate-600 hover:text-slate-900'
              }`}
            >
              Team Tasks ({tasks.length})
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('my_tasks')}
              className={`rounded-xl px-3 py-1.5 text-xs font-semibold transition ${
                activeTab === 'my_tasks'
                  ? 'bg-blue-600 text-white shadow-xs'
                  : 'bg-slate-100 text-slate-600 hover:text-slate-900'
              }`}
            >
              Assigned to Me by HR ({myAssignedTasks.length})
            </button>
          </div>

          {activeTab === 'team' && (
            <button
              type="button"
              onClick={() => setOpenAssign(true)}
              className="btn-primary text-xs self-start sm:self-auto"
            >
              Assign Task
            </button>
          )}
        </div>

        {/* Tab 1: Team Tasks */}
        {activeTab === 'team' && (
          <div>
            <DataTable
              columns={[
                { key: 'employee', label: 'Employee' },
                { key: 'name', label: 'Task' },
                { key: 'priority', label: 'Priority' },
                {
                  key: 'progress',
                  label: 'Progress',
                  render: (r) => (
                    <div className="flex items-center gap-2">
                      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-slate-100">
                        <div
                          className="h-full bg-blue-600 rounded-full"
                          style={{
                            width: `${Math.min(
                              100,
                              Math.max(
                                0,
                                r.progress !== undefined ? r.progress : r.status === 'Completed' ? 100 : 30
                              )
                            )}%`,
                          }}
                        />
                      </div>
                      <span className="text-xs text-slate-600">
                        {r.progress !== undefined ? r.progress : r.status === 'Completed' ? 100 : 30}%
                      </span>
                    </div>
                  ),
                },
                { key: 'status', label: 'Status', render: (r) => <StatusBadge status={r.status} /> },
                {
                  key: 'work_update',
                  label: 'Work Update / Blocker',
                  render: (r) => (
                    <span className={r.status === 'Blocked' ? 'text-red-600 font-medium' : 'text-slate-600'}>
                      {r.status === 'Blocked' && r.blocked_reason
                        ? `Blocker: ${r.blocked_reason}`
                        : r.work_update || '—'}
                    </span>
                  ),
                },
                { key: 'deadline', label: 'Deadline' },
              ]}
              rows={tasks}
            />
          </div>
        )}

        {/* Tab 2: Manager's Own Tasks Assigned by HR */}
        {activeTab === 'my_tasks' && (
          <div>
            {myAssignedTasks.length === 0 ? (
              <div className="p-8 text-center">
                <p className="text-sm font-semibold text-slate-700">No tasks currently assigned by HR</p>
                <p className="text-xs text-slate-400 mt-0.5">
                  When HR delegates organizational or department-level initiatives, they will appear here.
                </p>
              </div>
            ) : (
              <DataTable
                columns={[
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
                        <p className="font-semibold text-slate-900">{r.name || r.title}</p>
                        {r.description && <p className="text-[11px] text-slate-400 truncate max-w-xs">{r.description}</p>}
                      </div>
                    ),
                  },
                  { key: 'priority', label: 'Priority' },
                  {
                    key: 'progress',
                    label: 'My Progress',
                    render: (r) => (
                      <div className="flex items-center gap-2">
                        <div className="h-1.5 w-16 overflow-hidden rounded-full bg-slate-100">
                          <div
                            className={`h-full rounded-full ${
                              r.status === 'Completed'
                                ? 'bg-emerald-500'
                                : r.status === 'Blocked'
                                ? 'bg-red-500'
                                : 'bg-blue-600'
                            }`}
                            style={{ width: `${Math.min(100, Math.max(0, r.progress || 0))}%` }}
                          />
                        </div>
                        <span className="text-xs text-slate-600">{r.progress || 0}%</span>
                      </div>
                    ),
                  },
                  { key: 'status', label: 'Status', render: (r) => <StatusBadge status={r.status} /> },
                  { key: 'deadline', label: 'Deadline' },
                  {
                    key: 'work_update',
                    label: 'Progress Update / Blocker',
                    render: (r) => (
                      <div className="max-w-xs text-xs truncate">
                        {r.status === 'Blocked' && r.blocked_reason ? (
                          <span className="font-medium text-red-600">Blocker: {r.blocked_reason}</span>
                        ) : r.work_update ? (
                          <span className="text-slate-600">{r.work_update}</span>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </div>
                    ),
                  },
                  {
                    key: 'actions',
                    label: '',
                    render: (r) => (
                      <button
                        type="button"
                        onClick={() => handleOpenUpdateMy(r)}
                        className="btn-secondary text-xs py-1 px-2.5"
                      >
                        Update
                      </button>
                    ),
                  },
                ]}
                rows={myAssignedTasks}
              />
            )}
          </div>
        )}
      </div>

      {/* Assign Task Modal (Manager -> Employee) */}
      <Modal
        open={openAssign}
        title="Assign Task to Team Member"
        onClose={() => setOpenAssign(false)}
        footer={
          <>
            <button type="button" onClick={() => setOpenAssign(false)} className="btn-secondary">
              Cancel
            </button>
            <button
              type="button"
              disabled={busy || !form.name.trim()}
              className="btn-primary disabled:opacity-50"
              onClick={handleAssignTask}
            >
              {busy ? 'Assigning...' : 'Assign Task'}
            </button>
          </>
        }
      >
        <div className="space-y-3">
          <label className="block text-sm">
            Task Title
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="e.g. Complete module API tests"
              className="ww-input"
            />
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className="text-sm">
              Assign To
              <select
                value={form.employee_id}
                onChange={(e) => setForm({ ...form, employee_id: e.target.value })}
                className="ww-input"
              >
                {members.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.employee} ({m.id})
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm">
              Priority
              <select
                value={form.priority}
                onChange={(e) => setForm({ ...form, priority: e.target.value })}
                className="ww-input"
              >
                <option>High</option>
                <option>Medium</option>
                <option>Low</option>
              </select>
            </label>
          </div>
          <label className="block text-sm">
            Deadline
            <input
              type="text"
              value={form.deadline}
              onChange={(e) => setForm({ ...form, deadline: e.target.value })}
              placeholder="e.g. End of Week, 20 Oct"
              className="ww-input"
            />
          </label>
        </div>
      </Modal>

      {/* Update My Assigned Task Modal (Manager updating task assigned by HR) */}
      <Modal
        open={openUpdateMy}
        title={selectedMyTask ? `Update Progress: ${selectedMyTask.name || selectedMyTask.title}` : 'Update Task'}
        onClose={() => setOpenUpdateMy(false)}
        footer={
          <>
            <button type="button" onClick={() => setOpenUpdateMy(false)} className="btn-secondary text-xs">
              Cancel
            </button>
            <button
              type="button"
              disabled={busy}
              className="btn-primary text-xs disabled:opacity-50"
              onClick={handleSaveMyTaskUpdate}
            >
              {busy ? 'Saving...' : 'Save Progress'}
            </button>
          </>
        }
      >
        <div className="space-y-3 text-xs">
          {selectedMyTask?.verification_status === 'Changes Requested' && (
            <div className="rounded-lg bg-amber-50 border border-amber-300 p-2.5 text-xs text-amber-900">
              <span className="font-semibold text-amber-800">HR Requested Changes</span>
              <p className="mt-1 bg-white/80 p-2 rounded border border-amber-200">
                <strong>HR Feedback:</strong> {selectedMyTask.verification_notes || 'Please revise your deliverables and resubmit.'}
              </p>
              <p className="mt-1 text-[11px] text-amber-700">Update work and set progress to 100% to resubmit.</p>
            </div>
          )}
          {selectedMyTask?.status === 'Completed' && selectedMyTask?.verification_status !== 'Changes Requested' && (
            <div className="rounded-lg bg-emerald-50 border border-emerald-200 p-2.5 text-xs text-emerald-800">
              <span className="font-semibold">Task Completed (100%)</span>
              <p className="mt-0.5 text-emerald-700">This task is completed and locked from ordinary updates.</p>
            </div>
          )}
          {selectedMyTask?.status === 'Blocked' && (
            <div className="rounded-lg bg-red-50 border border-red-200 p-2.5 text-xs text-red-800">
              <span className="font-semibold">Task Blocked</span>
              <p className="mt-0.5 text-red-700">
                {selectedMyTask.blocked_reason || 'Deadline missed or dependencies blocking progress.'}
              </p>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <span className="block text-slate-700 font-medium">Automatic Status</span>
              <div className="mt-2">
                <StatusBadge
                  status={
                    selectedMyTask?.status === 'Completed'
                      ? 'Completed'
                      : selectedMyTask?.status === 'Blocked'
                      ? 'Blocked'
                      : deriveStatusFromProgress(updateForm.progress)
                  }
                />
              </div>
            </div>

            <label className="block text-slate-700 font-medium">
              Progress ({updateForm.progress}%)
              <input
                type="range"
                min="0"
                max="100"
                step="5"
                disabled={selectedMyTask?.status === 'Completed' || selectedMyTask?.status === 'Blocked'}
                value={updateForm.progress}
                onChange={(e) => setUpdateForm({ ...updateForm, progress: Number(e.target.value) })}
                className="w-full mt-2 disabled:opacity-50"
              />
            </label>
          </div>

          <label className="block text-slate-700 font-medium">
            Work Progress Update / Signal
            <textarea
              rows={3}
              value={updateForm.work_update}
              onChange={(e) => setUpdateForm({ ...updateForm, work_update: e.target.value })}
              placeholder="Provide a brief update on deliverables or current focus..."
              className="ww-input mt-1"
            />
          </label>
        </div>
      </Modal>
    </div>
  )
}
