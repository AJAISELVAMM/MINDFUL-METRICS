import { useEffect, useState, useMemo } from 'react'
import { Plus, Handshake, Calendar, AlertTriangle, CheckCircle, Clock } from 'lucide-react'
import StatCard from '../../components/common/StatCard'
import StatusBadge from '../../components/common/StatusBadge'
import Modal from '../../components/common/Modal'
import LoadingSkeleton from '../../components/common/LoadingSkeleton'
import ErrorState from '../../components/common/ErrorState'
import {
  getInterventions,
  createIntervention,
  updateIntervention,
  getInterventionCandidates,
  getEmployees,
} from '../../services/api'

export default function Interventions() {
  const [items, setItems] = useState([])
  const [candidates, setCandidates] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [filterStatus, setFilterStatus] = useState('ALL')

  // Modals
  const [openCreate, setOpenCreate] = useState(false)
  const [selectedItem, setSelectedItem] = useState(null)
  const [openUpdate, setOpenUpdate] = useState(false)

  // Forms
  const [form, setForm] = useState({
    employee_id: '',
    risk_level: 'High',
    trigger_reason: '',
    intervention_type: 'Workload Review',
    recommendation: '',
    follow_up_date: '',
    notes: '',
  })

  const [updateForm, setUpdateForm] = useState({
    status: 'OPEN',
    notes: '',
    resolution: '',
    follow_up_date: '',
  })

  useEffect(() => {
    loadData()
  }, [])

  async function loadData() {
    setLoading(true)
    setError('')
    try {
      const [data, candList, empList] = await Promise.all([
        getInterventions().catch(() => []),
        getInterventionCandidates().catch(() => []),
        getEmployees().catch(() => []),
      ])
      setItems(Array.isArray(data) ? data : [])
      const pool = candList.length > 0 ? candList : empList
      setCandidates(pool)
      if (pool.length > 0 && !form.employee_id) {
        setForm((f) => ({ ...f, employee_id: pool[0].id || pool[0].employee_id }))
      }
    } catch (e) {
      setError(e.message || 'Could not load interventions.')
    } finally {
      setLoading(false)
    }
  }

  async function handleCreate(e) {
    e.preventDefault()
    if (!form.employee_id) return
    setBusy(true)
    setError('')
    try {
      await createIntervention(form)
      setOpenCreate(false)
      setForm({
        employee_id: candidates[0]?.id || '',
        risk_level: 'High',
        trigger_reason: '',
        intervention_type: 'Workload Review',
        recommendation: '',
        follow_up_date: '',
        notes: '',
      })
      await loadData()
    } catch (err) {
      setError(err.message || 'Could not record intervention.')
    } finally {
      setBusy(false)
    }
  }

  function handleOpenUpdate(item) {
    setSelectedItem(item)
    setUpdateForm({
      status: item.status || 'OPEN',
      notes: item.notes || '',
      resolution: item.resolution || '',
      follow_up_date: item.follow_up_date || '',
    })
    setOpenUpdate(true)
  }

  async function handleUpdate(e) {
    e.preventDefault()
    if (!selectedItem) return
    setBusy(true)
    setError('')
    try {
      await updateIntervention(selectedItem.id, updateForm)
      setOpenUpdate(false)
      setSelectedItem(null)
      await loadData()
    } catch (err) {
      setError(err.message || 'Could not update intervention.')
    } finally {
      setBusy(false)
    }
  }

  const filtered = useMemo(() => {
    if (filterStatus === 'ALL') return items
    return items.filter((it) => (it.status || 'OPEN').toUpperCase() === filterStatus)
  }, [items, filterStatus])

  const counts = useMemo(() => {
    const total = items.length
    const open = items.filter((i) => (i.status || 'OPEN').toUpperCase() === 'OPEN').length
    const inProgress = items.filter((i) => (i.status || '').toUpperCase() === 'IN_PROGRESS').length
    const resolved = items.filter((i) => (i.status || '').toUpperCase() === 'RESOLVED').length
    return { total, open, inProgress, resolved }
  }, [items])

  if (loading) return <LoadingSkeleton rows={3} />
  if (error && items.length === 0) {
    return <ErrorState message={error} onRetry={loadData} />
  }

  return (
    <div className="page-stack fade-in">
      {/* KPI Summary Cards */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatCard label="Total Interventions" value={counts.total} />
        <StatCard label="Open Cases" value={counts.open} tone="high" />
        <StatCard label="In Progress" value={counts.inProgress} tone="mod" />
        <StatCard label="Resolved" value={counts.resolved} tone="low" />
      </div>

      {/* Action Bar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs text-slate-500">
            Workplace support cases initiated from wellbeing signals, burnout risk scores, and workload patterns.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center rounded-xl bg-white p-1 border border-slate-200 text-xs">
            {['ALL', 'OPEN', 'IN_PROGRESS', 'RESOLVED'].map((st) => (
              <button
                key={st}
                type="button"
                onClick={() => setFilterStatus(st)}
                className={`rounded-lg px-2.5 py-1 font-medium transition ${
                  filterStatus === st
                    ? 'bg-blue-600 text-white shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {st === 'ALL' ? 'All' : st === 'IN_PROGRESS' ? 'In Progress' : st.charAt(0) + st.slice(1).toLowerCase()}
              </button>
            ))}
          </div>
          <button
            type="button"
            onClick={() => setOpenCreate(true)}
            className="btn-primary flex items-center gap-1.5 text-xs whitespace-nowrap"
          >
            <Plus size={14} />
            <span>Record Intervention</span>
          </button>
        </div>
      </div>

      {/* Main Content: List of Interventions or Empty State */}
      {filtered.length === 0 ? (
        <div className="card p-8 text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-blue-50 text-blue-600">
            <Handshake size={24} />
          </div>
          <h3 className="text-sm font-semibold text-slate-800">
            {items.length === 0 ? 'No Active Workplace Interventions' : 'No Interventions Match Selected Filter'}
          </h3>
          <p className="mt-1 text-xs text-slate-500 max-w-md mx-auto">
            {items.length === 0
              ? "All employees are currently within standard risk parameters. Use 'Record Intervention' when concerning workload or burnout indicators are identified."
              : 'Try selecting a different status filter above to view existing intervention cases.'}
          </p>
          {items.length === 0 && (
            <button
              type="button"
              onClick={() => setOpenCreate(true)}
              className="btn-primary mt-4 text-xs"
            >
              Record First Intervention
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          {filtered.map((it) => (
            <div key={it.id} className="card p-5">
              <div className="flex flex-wrap items-start justify-between gap-2 border-b border-slate-100 pb-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold text-blue-600">{it.id}</span>
                    <h4 className="font-semibold text-slate-900">
                      {it.employee} · {it.empId}
                    </h4>
                    <span className="text-xs text-slate-400">({it.department})</span>
                  </div>
                  <p className="mt-1 text-xs text-slate-600">
                    <span className="font-medium text-slate-700">Type:</span> {it.intervention_type}
                    {it.created_by ? ` · Recorded by ${it.created_by}` : ''}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium ${
                      it.risk_level === 'High'
                        ? 'bg-red-50 text-red-700 border border-red-200'
                        : it.risk_level === 'Moderate'
                        ? 'bg-amber-50 text-amber-700 border border-amber-200'
                        : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                    }`}
                  >
                    {it.risk_level} Risk
                  </span>
                  <StatusBadge status={it.status} />
                  <button
                    type="button"
                    onClick={() => handleOpenUpdate(it)}
                    className="btn-secondary text-xs ml-2"
                  >
                    Update
                  </button>
                </div>
              </div>

              <div className="mt-3 grid gap-3 sm:grid-cols-2 text-xs">
                <div>
                  <span className="font-medium text-slate-500">Trigger Indicator:</span>
                  <p className="mt-0.5 text-slate-800">{it.trigger_reason || 'Workload indicator alert'}</p>
                </div>
                <div>
                  <span className="font-medium text-slate-500">Recommended Action:</span>
                  <p className="mt-0.5 text-slate-800">{it.recommendation || 'Workload rebalancing & 1-on-1'}</p>
                </div>
              </div>

              {it.notes && (
                <div className="mt-3 rounded-lg bg-slate-50 p-2.5 text-xs text-slate-700 border border-slate-200">
                  <span className="font-medium text-slate-900">Notes & Follow-up: </span>
                  {it.notes}
                  {it.follow_up_date && (
                    <span className="ml-2 text-blue-600 font-medium">
                      (Follow-up: {it.follow_up_date})
                    </span>
                  )}
                </div>
              )}

              {it.resolution && (
                <div className="mt-2 rounded-lg bg-emerald-50 p-2.5 text-xs text-emerald-800 border border-emerald-200">
                  <span className="font-medium">Resolution: </span>
                  {it.resolution}
                </div>
              )}

              {it.timeline && it.timeline.length > 0 && (
                <ol className="mt-4 space-y-1.5 border-l border-slate-200 pl-4 text-xs">
                  {it.timeline.map((t, idx) => (
                    <li key={idx} className="text-slate-600">
                      <span className="text-[11px] text-slate-400 font-mono">{t.date}</span> — {t.event}
                    </li>
                  ))}
                </ol>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Record Intervention Modal */}
      <Modal
        open={openCreate}
        title="Record Workplace Intervention"
        onClose={() => setOpenCreate(false)}
        footer={
          <>
            <button type="button" onClick={() => setOpenCreate(false)} className="btn-secondary text-xs">
              Cancel
            </button>
            <button
              type="button"
              disabled={busy || !form.employee_id}
              className="btn-primary text-xs disabled:opacity-50"
              onClick={handleCreate}
            >
              {busy ? 'Recording...' : 'Record Intervention'}
            </button>
          </>
        }
      >
        <div className="space-y-3 text-xs">
          <label className="block text-slate-700 font-medium">
            Subject Employee
            <select
              value={form.employee_id}
              onChange={(e) => setForm({ ...form, employee_id: e.target.value })}
              className="ww-input mt-1"
            >
              {candidates.map((c) => (
                <option key={c.id || c.employee_id} value={c.id || c.employee_id}>
                  {c.name} ({c.employee_id || `E${c.id}`}) — {c.department}
                  {c.risk_score ? ` [Risk ${c.risk_score}]` : ''}
                </option>
              ))}
            </select>
          </label>

          <div className="grid grid-cols-2 gap-3">
            <label className="block text-slate-700 font-medium">
              Intervention Type
              <select
                value={form.intervention_type}
                onChange={(e) => setForm({ ...form, intervention_type: e.target.value })}
                className="ww-input mt-1"
              >
                <option>Workload Review</option>
                <option>1-on-1 Wellbeing Sync</option>
                <option>Task Redistribution</option>
                <option>Schedule Adjustment</option>
                <option>Wellness Support</option>
              </select>
            </label>

            <label className="block text-slate-700 font-medium">
              Observed Risk Level
              <select
                value={form.risk_level}
                onChange={(e) => setForm({ ...form, risk_level: e.target.value })}
                className="ww-input mt-1"
              >
                <option>High</option>
                <option>Moderate</option>
                <option>Low</option>
              </select>
            </label>
          </div>

          <label className="block text-slate-700 font-medium">
            Trigger Indicator / Reason
            <input
              type="text"
              value={form.trigger_reason}
              onChange={(e) => setForm({ ...form, trigger_reason: e.target.value })}
              placeholder="e.g. Elevated overtime (>12 hrs/wk) & multiple blocked deliverables"
              className="ww-input mt-1"
            />
          </label>

          <label className="block text-slate-700 font-medium">
            Recommended Action
            <input
              type="text"
              value={form.recommendation}
              onChange={(e) => setForm({ ...form, recommendation: e.target.value })}
              placeholder="e.g. Discuss capacity with manager; reassign sprint overflow"
              className="ww-input mt-1"
            />
          </label>

          <div className="grid grid-cols-2 gap-3">
            <label className="block text-slate-700 font-medium">
              Follow-up Target Date
              <input
                type="date"
                value={form.follow_up_date}
                onChange={(e) => setForm({ ...form, follow_up_date: e.target.value })}
                className="ww-input mt-1"
              />
            </label>
            <label className="block text-slate-700 font-medium">
              Initial Notes
              <input
                type="text"
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
                placeholder="Initial check-in scheduled"
                className="ww-input mt-1"
              />
            </label>
          </div>
        </div>
      </Modal>

      {/* Update Intervention Modal */}
      <Modal
        open={openUpdate}
        title={`Update Intervention: ${selectedItem?.id || ''}`}
        onClose={() => setOpenUpdate(false)}
        footer={
          <>
            <button type="button" onClick={() => setOpenUpdate(false)} className="btn-secondary text-xs">
              Cancel
            </button>
            <button
              type="button"
              disabled={busy}
              className="btn-primary text-xs disabled:opacity-50"
              onClick={handleUpdate}
            >
              {busy ? 'Saving...' : 'Save Updates'}
            </button>
          </>
        }
      >
        <div className="space-y-3 text-xs">
          <label className="block text-slate-700 font-medium">
            Case Status
            <select
              value={updateForm.status}
              onChange={(e) => setUpdateForm({ ...updateForm, status: e.target.value })}
              className="ww-input mt-1"
            >
              <option value="OPEN">OPEN (Under Initial Review)</option>
              <option value="IN_PROGRESS">IN_PROGRESS (Actions Ongoing)</option>
              <option value="RESOLVED">RESOLVED (Outcome Achieved)</option>
            </select>
          </label>

          <label className="block text-slate-700 font-medium">
            Notes & Progress Updates
            <textarea
              rows={3}
              value={updateForm.notes}
              onChange={(e) => setUpdateForm({ ...updateForm, notes: e.target.value })}
              placeholder="Enter details on meetings conducted, schedule adjustments, or check-in outcomes..."
              className="ww-input mt-1"
            />
          </label>

          <label className="block text-slate-700 font-medium">
            Next Follow-up Date
            <input
              type="date"
              value={updateForm.follow_up_date}
              onChange={(e) => setUpdateForm({ ...updateForm, follow_up_date: e.target.value })}
              className="ww-input mt-1"
            />
          </label>

          {updateForm.status === 'RESOLVED' && (
            <label className="block text-slate-700 font-medium">
              Resolution Summary
              <textarea
                rows={2}
                value={updateForm.resolution}
                onChange={(e) => setUpdateForm({ ...updateForm, resolution: e.target.value })}
                placeholder="Describe how workload was stabilized or support was delivered..."
                className="ww-input mt-1"
              />
            </label>
          )}
        </div>
      </Modal>
    </div>
  )
}
