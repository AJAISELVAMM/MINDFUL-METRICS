import { useEffect, useMemo, useState } from 'react'
import StatCard from '../../components/common/StatCard'
import DataTable from '../../components/common/DataTable'
import StatusBadge from '../../components/common/StatusBadge'
import Modal from '../../components/common/Modal'
import { getHRLeaves, updateLeaveRequest } from '../../services/api'
import LoadingSkeleton from '../../components/common/LoadingSkeleton'
import ErrorState from '../../components/common/ErrorState'

export default function HRLeave() {
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [confirm, setConfirm] = useState(null)

  // Filters
  const [searchEmp, setSearchEmp] = useState('')
  const [filterDept, setFilterDept] = useState('All')
  const [filterRole, setFilterRole] = useState('All')
  const [filterType, setFilterType] = useState('All')
  const [filterStatus, setFilterStatus] = useState('All')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  useEffect(() => {
    loadLeaves()
  }, [])

  async function loadLeaves() {
    setLoading(true)
    setError('')
    try {
      const data = await getHRLeaves()
      setRows(data)
    } catch (e) {
      setError(e.message || 'Could not load leave records.')
    } finally {
      setLoading(false)
    }
  }

  async function handleAction(id, status) {
    if (busy) return
    setBusy(true)
    setError('')
    try {
      setRows((rs) => rs.map((r) => (r.id === id ? { ...r, status, final_status: status } : r)))
      setConfirm(null)
      await updateLeaveRequest(id, status)
    } catch (e) {
      setError(e.message || 'Could not update leave request.')
      await loadLeaves()
    } finally {
      setBusy(false)
    }
  }

  const filtered = useMemo(() => {
    return rows.filter((r) => {
      const empMatch =
        !searchEmp ||
        (r.employee || '').toLowerCase().includes(searchEmp.toLowerCase()) ||
        (r.employee_id || '').toLowerCase().includes(searchEmp.toLowerCase())
      const deptMatch = filterDept === 'All' || r.department === filterDept
      const roleMatch = filterRole === 'All' || (r.role || '').toLowerCase() === filterRole.toLowerCase()
      const typeMatch = filterType === 'All' || (r.leave_type || r.type) === filterType
      const statusMatch = filterStatus === 'All' || (r.status || '').toLowerCase() === filterStatus.toLowerCase()
      return empMatch && deptMatch && roleMatch && typeMatch && statusMatch
    })
  }, [rows, searchEmp, filterDept, filterRole, filterType, filterStatus])

  if (loading) return <LoadingSkeleton rows={3} />
  if (error && !rows.length) return <ErrorState message={error} onRetry={loadLeaves} />

  const pendingCount = rows.filter((r) => r.status === 'Pending').length
  const approvedCount = rows.filter((r) => r.status === 'Approved').length
  const rejectedCount = rows.filter((r) => r.status === 'Rejected').length

  return (
    <div className="page-stack fade-in">
      {error && <p className="text-sm text-red-600" role="alert">{error}</p>}
      <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
        <StatCard label="Total Requests" value={rows.length} tone="blue" />
        <StatCard label="Pending Approval" value={pendingCount} tone="mod" />
        <StatCard label="Approved" value={approvedCount} tone="low" />
        <StatCard label="Rejected" value={rejectedCount} />
      </div>

      {/* Filter Toolbar */}
      <div className="card p-4">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">Filter Organization Leaves</p>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
          <input
            type="text"
            placeholder="Search employee / ID..."
            value={searchEmp}
            onChange={(e) => setSearchEmp(e.target.value)}
            className="ww-input mt-0 text-xs"
          />
          <select value={filterDept} onChange={(e) => setFilterDept(e.target.value)} className="ww-input mt-0 text-xs">
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
          <select value={filterRole} onChange={(e) => setFilterRole(e.target.value)} className="ww-input mt-0 text-xs">
            <option value="All">All Roles</option>
            <option value="employee">Employee</option>
            <option value="manager">Manager</option>
            <option value="hr">HR</option>
          </select>
          <select value={filterType} onChange={(e) => setFilterType(e.target.value)} className="ww-input mt-0 text-xs">
            <option value="All">All Leave Types</option>
            <option>Casual Leave</option>
            <option>Sick Leave</option>
            <option>Earned Leave</option>
          </select>
          <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)} className="ww-input mt-0 text-xs">
            <option value="All">All Statuses</option>
            <option value="Pending">Pending</option>
            <option value="Approved">Approved</option>
            <option value="Rejected">Rejected</option>
          </select>
        </div>
      </div>

      {/* Detailed Organization Table */}
      <div className="card overflow-x-auto p-4">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-800">Organization Leave Records ({filtered.length})</h3>
        </div>
        <DataTable
          columns={[
            {
              key: 'employee',
              label: 'Employee',
              render: (r) => (
                <div>
                  <p className="font-semibold text-slate-800">{r.employee}</p>
                  <p className="text-[11px] text-slate-400">{r.employee_id || r.empId}</p>
                </div>
              ),
            },
            { key: 'department', label: 'Department' },
            { key: 'role', label: 'Role', render: (r) => <span className="capitalize">{r.role}</span> },
            { key: 'leave_type', label: 'Leave Type' },
            {
              key: 'dates',
              label: 'Date / Duration',
              render: (r) => (
                <div>
                  <p className="text-xs">{r.from_date || r.date}</p>
                  <p className="text-[11px] text-slate-500">{r.duration}</p>
                </div>
              ),
            },
            { key: 'reason', label: 'Reason' },
            { key: 'applied_date', label: 'Applied On' },
            {
              key: 'manager_approval',
              label: 'Mgr Status',
              render: (r) => <StatusBadge status={r.manager_approval || r.status} />,
            },
            {
              key: 'status',
              label: 'Final Status',
              render: (r) => <StatusBadge status={r.status} />,
            },
            {
              key: 'approver',
              label: 'Approver',
              render: (r) => (
                <div>
                  <p className="text-xs">{r.approver || '—'}</p>
                  <p className="text-[10px] text-slate-400">{r.approval_timestamp || ''}</p>
                </div>
              ),
            },
            {
              key: 'action',
              label: 'Action',
              render: (r) =>
                r.status === 'Pending' ? (
                  <div className="flex gap-2">
                    <button
                      type="button"
                      className="text-xs font-medium text-emerald-600 hover:underline"
                      onClick={() => setConfirm({ id: r.id, status: 'Approved' })}
                    >
                      Approve
                    </button>
                    <button
                      type="button"
                      className="text-xs font-medium text-red-500 hover:underline"
                      onClick={() => setConfirm({ id: r.id, status: 'Rejected' })}
                    >
                      Reject
                    </button>
                  </div>
                ) : (
                  <span className="text-xs text-slate-400">—</span>
                ),
            },
          ]}
          rows={filtered}
        />
      </div>

      <Modal
        open={!!confirm}
        title="Confirm Leave Action"
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
        <p className="text-sm">Mark this leave request as <span className="font-semibold">{confirm?.status}</span>?</p>
      </Modal>
    </div>
  )
}
