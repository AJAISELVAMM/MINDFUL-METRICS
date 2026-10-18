import { useEffect, useState } from 'react'
import StatCard from '../../components/common/StatCard'
import DataTable from '../../components/common/DataTable'
import StatusBadge from '../../components/common/StatusBadge'
import Modal from '../../components/common/Modal'
import EmptyState from '../../components/common/EmptyState'
import { applyLeave, getLeaveData, cancelLeave } from '../../services/api'
import ErrorState from '../../components/common/ErrorState'
import LoadingSkeleton from '../../components/common/LoadingSkeleton'

export default function Leave() {
  const [balance, setBalance] = useState([])
  const [history, setHistory] = useState([])
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({
    type: 'Casual Leave',
    start: '',
    end: '',
    half_day_session: 'FULL_DAY',
    reason: '',
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    loadLeaves()
  }, [])

  async function loadLeaves() {
    setLoading(true)
    setError('')
    try {
      const d = await getLeaveData()
      setBalance(d.balance || [])
      setHistory(d.history || [])
    } catch {
      setError('Leave data could not be loaded.')
    } finally {
      setLoading(false)
    }
  }

  async function handleCancel(id) {
    if (!confirm('Are you sure you want to cancel this pending leave request?')) return
    try {
      await cancelLeave(id)
      await loadLeaves()
    } catch (e) {
      setError(e.message || 'Could not cancel leave request.')
    }
  }

  async function submit() {
    if (busy) return
    if (!form.start) {
      setError('Choose a start date.')
      return
    }
    const end = form.end || form.start
    if (new Date(end) < new Date(form.start)) {
      setError('End date cannot be earlier than start date.')
      return
    }
    if (!form.reason.trim()) {
      setError('Add a reason for your leave request.')
      return
    }
    setBusy(true)
    setError('')
    try {
      const dur = form.half_day_session === 'FULL_DAY' ? '1 day' : '0.5 day'
      const res = await applyLeave({
        type: form.type,
        leave_type: form.type,
        start: form.start,
        end: end,
        date: `${form.start}${end !== form.start ? ` – ${end}` : ''}`,
        duration: dur,
        half_day_session: form.half_day_session,
        reason: form.reason,
      })
      setHistory((h) => [{ ...res.item, date: form.start }, ...h])
      setOpen(false)
      setForm({ type: 'Casual Leave', start: '', end: '', half_day_session: 'FULL_DAY', reason: '' })
      await loadLeaves()
    } catch (e) {
      setError(e.message || 'Leave request could not be submitted.')
    } finally {
      setBusy(false)
    }
  }

  if (loading) return <LoadingSkeleton rows={2} />
  if (error && !balance.length) return <ErrorState message={error} onRetry={loadLeaves} />

  return (
    <div className="page-stack fade-in">
      {error && <p className="text-sm text-red-600" role="alert">{error}</p>}
      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        {balance.map((b) => (
          <StatCard key={b.type} label={b.type} value={`${b.remaining} Days`} hint={`${b.total} allocated`} tone="blue" />
        ))}
      </div>
      <div className="flex justify-end">
        <button type="button" onClick={() => setOpen(true)} className="btn-primary">Apply Leave</button>
      </div>
      <div className="card p-4">
        <h3 className="mb-3 text-sm font-semibold">Leave History</h3>
        {history.length ? (
          <DataTable
            columns={[
              { key: 'date', label: 'Date' },
              { key: 'type', label: 'Type' },
              {
                key: 'duration',
                label: 'Duration',
                render: (r) => (
                  <span>
                    {r.duration}{' '}
                    {r.half_day_session === 'MORNING_HALF_DAY' && (
                      <span className="text-[10px] text-amber-600">(Morning)</span>
                    )}
                    {r.half_day_session === 'AFTERNOON_HALF_DAY' && (
                      <span className="text-[10px] text-amber-600">(Afternoon)</span>
                    )}
                  </span>
                ),
              },
              { key: 'reason', label: 'Reason' },
              { key: 'status', label: 'Status', render: (r) => <StatusBadge status={r.status} /> },
              {
                key: 'action',
                label: 'Action',
                render: (r) =>
                  r.status === 'Pending' ? (
                    <button
                      type="button"
                      onClick={() => handleCancel(r.id)}
                      className="text-xs text-red-600 hover:text-red-800 font-medium"
                    >
                      Cancel
                    </button>
                  ) : null,
              },
            ]}
            rows={history}
          />
        ) : (
          <EmptyState title="No leave requests found." />
        )}
      </div>

      <Modal
        open={open}
        title="Apply Leave"
        onClose={() => setOpen(false)}
        footer={
          <>
            <button type="button" className="btn-secondary" onClick={() => setOpen(false)}>Cancel</button>
            <button type="button" disabled={busy} className="btn-primary disabled:opacity-50" onClick={submit}>
              {busy ? 'Submitting...' : 'Submit Request'}
            </button>
          </>
        }
      >
        <label className="block text-sm font-medium">Leave Type
          <select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })} className="ww-input">
            <option>Casual Leave</option>
            <option>Sick Leave</option>
            <option>Earned Leave</option>
          </select>
        </label>
        <div className="mt-3 grid grid-cols-2 gap-3">
          <label className="text-sm font-medium">Start Date
            <input type="date" value={form.start} onChange={(e) => setForm({ ...form, start: e.target.value })} className="ww-input" />
          </label>
          <label className="text-sm font-medium">End Date
            <input type="date" value={form.end} onChange={(e) => setForm({ ...form, end: e.target.value })} className="ww-input" />
          </label>
        </div>
        <label className="mt-3 block text-sm font-medium">Leave Session
          <select
            value={form.half_day_session}
            onChange={(e) => setForm({ ...form, half_day_session: e.target.value })}
            className="ww-input"
          >
            <option value="FULL_DAY">Full Day</option>
            <option value="MORNING_HALF_DAY">Morning Half-Day (09:00 AM – 01:00 PM)</option>
            <option value="AFTERNOON_HALF_DAY">Afternoon Half-Day (01:00 PM – 05:30 PM)</option>
          </select>
        </label>
        <label className="mt-3 block text-sm font-medium">Reason
          <textarea
            value={form.reason}
            onChange={(e) => setForm({ ...form, reason: e.target.value })}
            className="ww-input"
            rows={3}
            placeholder="Provide context for this leave..."
          />
        </label>
      </Modal>
    </div>
  )
}
