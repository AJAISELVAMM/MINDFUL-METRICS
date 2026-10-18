import { useEffect, useState } from 'react'
import StatCard from '../../components/common/StatCard'
import DataTable from '../../components/common/DataTable'
import StatusBadge from '../../components/common/StatusBadge'
import Modal from '../../components/common/Modal'
import { getTeamLeave, updateLeaveRequest } from '../../services/api'
import ErrorState from '../../components/common/ErrorState'
import LoadingSkeleton from '../../components/common/LoadingSkeleton'

export default function LeaveRequests() {
  const [rows, setRows] = useState([])
  const [confirm, setConfirm] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => { getTeamLeave().then(setRows).catch(() => setError('Leave requests could not be loaded.')).finally(() => setLoading(false)) }, [])

  async function act(id, status) {
    if (busy) return
    setBusy(true); setError('')
    try {
      setRows((rs) => rs.map((r) => (r.id === id ? { ...r, status } : r)))
      setConfirm(null)
      await updateLeaveRequest(id, status)
    }
    catch (e) {
      setError(e.message || 'Leave request could not be updated.')
      getTeamLeave().then(setRows).catch(() => {})
    }
    finally { setBusy(false) }
  }

  if (loading) return <LoadingSkeleton rows={2} />
  if (error && !rows.length) return <ErrorState message={error} onRetry={() => window.location.reload()} />

  const pending = rows.filter((r) => r.status === 'Pending').length
  return (
    <div className="page-stack fade-in">
      {error && <p className="text-sm text-red-600" role="alert">{error}</p>}
      <div className="grid grid-cols-3 gap-3">
        <StatCard label="Pending" value={pending} tone="mod" />
        <StatCard label="Approved" value={rows.filter((r) => r.status === 'Approved').length} tone="low" />
        <StatCard label="Rejected" value={rows.filter((r) => r.status === 'Rejected').length} />
      </div>
      <div className="card p-4">
        <DataTable
          columns={[
            { key: 'employee', label: 'Employee' },
            { key: 'type', label: 'Leave Type' },
            { key: 'date', label: 'Date' },
            { key: 'duration', label: 'Duration' },
            { key: 'reason', label: 'Reason' },
            { key: 'status', label: 'Status', render: (r) => <StatusBadge status={r.status} /> },
            { key: 'a', label: 'Actions', render: (r) => r.status === 'Pending' ? (
              <div className="flex gap-2">
                <button type="button" className="text-xs font-medium text-emerald-600" onClick={() => setConfirm({ id: r.id, status: 'Approved' })}>Approve</button>
                <button type="button" className="text-xs font-medium text-red-500" onClick={() => setConfirm({ id: r.id, status: 'Rejected' })}>Reject</button>
              </div>
            ) : '—'},
          ]}
          rows={rows}
        />
      </div>
      <Modal open={!!confirm} title="Confirm action" onClose={() => setConfirm(null)} footer={
        <>
          <button type="button" onClick={() => setConfirm(null)} className="text-sm">Cancel</button>
          <button type="button" disabled={busy} className="btn-primary disabled:opacity-50" onClick={() => act(confirm.id, confirm.status)}>{busy ? 'Saving...' : 'Confirm'}</button>
        </>
      }>
        <p className="text-sm">Mark this request as {confirm?.status}?</p>
      </Modal>
    </div>
  )
}
