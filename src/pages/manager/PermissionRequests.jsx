import { useEffect, useState } from 'react'
import StatCard from '../../components/common/StatCard'
import DataTable from '../../components/common/DataTable'
import StatusBadge from '../../components/common/StatusBadge'
import Modal from '../../components/common/Modal'
import { getTeamPermissions, updatePermission, getMyPermissions, applyPermission } from '../../services/api'
import LoadingSkeleton from '../../components/common/LoadingSkeleton'
import ErrorState from '../../components/common/ErrorState'

export default function PermissionRequests() {
  const [tab, setTab] = useState('team') // 'team' or 'my'
  const [teamRows, setTeamRows] = useState([])
  const [myRows, setMyRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [confirm, setConfirm] = useState(null)

  // Apply permission modal
  const [applyOpen, setApplyOpen] = useState(false)
  const [permForm, setPermForm] = useState({
    date: new Date().toISOString().split('T')[0],
    requested_checkout_time: '04:30 PM',
    reason: '',
  })

  useEffect(() => {
    loadData()
  }, [])

  async function loadData() {
    setLoading(true)
    setError('')
    try {
      const [tRows, mRows] = await Promise.all([getTeamPermissions(), getMyPermissions()])
      setTeamRows(tRows)
      setMyRows(mRows)
    } catch (e) {
      setError(e.message || 'Could not load permission requests.')
    } finally {
      setLoading(false)
    }
  }

  async function handleAction(id, status) {
    setBusy(true)
    setError('')
    try {
      await updatePermission(id, status)
      setTeamRows((rs) => rs.map((r) => (r.id === id ? { ...r, status } : r)))
      setConfirm(null)
    } catch (e) {
      setError(e.message || 'Could not update permission request.')
    } finally {
      setBusy(false)
    }
  }

  async function submitMyPermission(e) {
    e.preventDefault()
    if (!permForm.reason.trim()) {
      setError('Please provide a reason for early checkout.')
      return
    }
    setBusy(true)
    setError('')
    try {
      const res = await applyPermission(permForm)
      setMyRows((prev) => [res.item, ...prev])
      setApplyOpen(false)
      setPermForm({
        date: new Date().toISOString().split('T')[0],
        requested_checkout_time: '04:30 PM',
        reason: '',
      })
    } catch (e) {
      setError(e.message || 'Could not submit permission request.')
    } finally {
      setBusy(false)
    }
  }

  if (loading) return <LoadingSkeleton rows={2} />
  if (error && !teamRows.length && !myRows.length) return <ErrorState message={error} onRetry={loadData} />

  const pendingCount = teamRows.filter((r) => r.status === 'Pending').length
  const approvedCount = teamRows.filter((r) => r.status === 'Approved').length

  return (
    <div className="page-stack fade-in">
      {error && <p className="text-sm text-red-600" role="alert">{error}</p>}
      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <StatCard label="Pending Team Permissions" value={pendingCount} tone="mod" />
        <StatCard label="Approved Team Permissions" value={approvedCount} tone="low" />
        <StatCard label="My Permissions" value={myRows.length} tone="blue" />
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-2">
          <button
            type="button"
            className={`rounded-full px-4 py-1.5 text-xs font-semibold transition ${
              tab === 'team' ? 'bg-[#1E6BFF] text-white shadow-sm' : 'border border-[#E2EAF2] bg-white text-[#64748B]'
            }`}
            onClick={() => setTab('team')}
          >
            Team Requests ({teamRows.length})
          </button>
          <button
            type="button"
            className={`rounded-full px-4 py-1.5 text-xs font-semibold transition ${
              tab === 'my' ? 'bg-[#1E6BFF] text-white shadow-sm' : 'border border-[#E2EAF2] bg-white text-[#64748B]'
            }`}
            onClick={() => setTab('my')}
          >
            My Permissions ({myRows.length})
          </button>
        </div>
        <button type="button" onClick={() => setApplyOpen(true)} className="btn-primary">
          Apply Permission
        </button>
      </div>

      {tab === 'team' ? (
        <div className="card p-4">
          <h3 className="mb-3 text-sm font-semibold">Team Early Checkout Requests</h3>
          <DataTable
            columns={[
              { key: 'employee', label: 'Employee' },
              { key: 'department', label: 'Department' },
              { key: 'date', label: 'Date' },
              { key: 'requested_checkout_time', label: 'Requested Checkout' },
              { key: 'reason', label: 'Reason' },
              { key: 'status', label: 'Status', render: (r) => <StatusBadge status={r.status} /> },
              {
                key: 'actions',
                label: 'Actions',
                render: (r) =>
                  r.status === 'Pending' ? (
                    <div className="flex gap-2">
                      <button
                        type="button"
                        className="text-xs font-medium text-emerald-600 hover:underline"
                        onClick={() => setConfirm({ id: r.id, status: 'Approve' })}
                      >
                        Approve
                      </button>
                      <button
                        type="button"
                        className="text-xs font-medium text-red-500 hover:underline"
                        onClick={() => setConfirm({ id: r.id, status: 'Reject' })}
                      >
                        Reject
                      </button>
                    </div>
                  ) : (
                    '—'
                  ),
              },
            ]}
            rows={teamRows}
          />
        </div>
      ) : (
        <div className="card p-4">
          <h3 className="mb-3 text-sm font-semibold">My Permission History</h3>
          <DataTable
            columns={[
              { key: 'date', label: 'Date' },
              { key: 'requested_checkout_time', label: 'Requested Checkout' },
              { key: 'reason', label: 'Reason' },
              { key: 'status', label: 'Status', render: (r) => <StatusBadge status={r.status} /> },
              { key: 'approver', label: 'Approver' },
              { key: 'applied_at', label: 'Applied At' },
            ]}
            rows={myRows}
          />
        </div>
      )}

      {/* Confirmation Modal */}
      <Modal
        open={!!confirm}
        title="Confirm Permission Action"
        onClose={() => setConfirm(null)}
        footer={
          <>
            <button type="button" onClick={() => setConfirm(null)} className="btn-secondary">
              Cancel
            </button>
            <button
              type="button"
              disabled={busy}
              className="btn-primary disabled:opacity-50"
              onClick={() => handleAction(confirm.id, confirm.status)}
            >
              {busy ? 'Saving...' : 'Confirm'}
            </button>
          </>
        }
      >
        <p className="text-sm">
          Are you sure you want to {confirm?.status.toLowerCase()} this early checkout permission?
        </p>
      </Modal>

      {/* Apply Permission Modal */}
      <Modal
        open={applyOpen}
        title="Apply Early Checkout Permission"
        onClose={() => setApplyOpen(false)}
        footer={
          <>
            <button type="button" onClick={() => setApplyOpen(false)} className="btn-secondary">
              Cancel
            </button>
            <button
              type="button"
              disabled={busy}
              className="btn-primary disabled:opacity-50"
              onClick={submitMyPermission}
            >
              {busy ? 'Submitting...' : 'Submit Request'}
            </button>
          </>
        }
      >
        <div className="space-y-3">
          <label className="block text-sm">
            Date
            <input
              type="date"
              value={permForm.date}
              onChange={(e) => setPermForm({ ...permForm, date: e.target.value })}
              className="ww-input"
            />
          </label>
          <label className="block text-sm">
            Requested Checkout Time
            <select
              value={permForm.requested_checkout_time}
              onChange={(e) => setPermForm({ ...permForm, requested_checkout_time: e.target.value })}
              className="ww-input"
            >
              <option value="03:30 PM">03:30 PM</option>
              <option value="04:00 PM">04:00 PM</option>
              <option value="04:30 PM">04:30 PM</option>
              <option value="04:45 PM">04:45 PM</option>
            </select>
          </label>
          <label className="block text-sm">
            Reason
            <textarea
              rows={3}
              value={permForm.reason}
              onChange={(e) => setPermForm({ ...permForm, reason: e.target.value })}
              placeholder="e.g. Doctor appointment, urgent family matter..."
              className="ww-input"
            />
          </label>
        </div>
      </Modal>
    </div>
  )
}
