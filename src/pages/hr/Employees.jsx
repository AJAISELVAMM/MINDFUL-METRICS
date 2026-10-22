import { useEffect, useMemo, useState } from 'react'
import DataTable from '../../components/common/DataTable'
import RiskBadge from '../../components/common/RiskBadge'
import StatusBadge from '../../components/common/StatusBadge'
import EmployeeDetailDrawer from '../../components/common/EmployeeDetailDrawer'
import LoadingSkeleton from '../../components/common/LoadingSkeleton'
import ErrorState from '../../components/common/ErrorState'
import { getEmployees } from '../../services/api'

export default function Employees() {
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [q, setQ] = useState('')
  const [dept, setDept] = useState('All')
  const [risk, setRisk] = useState('All')
  const [page, setPage] = useState(0)
  const [sel, setSel] = useState(null)
  const pageSize = 6

  function loadEmployees() {
    setLoading(true)
    setError('')
    getEmployees()
      .then((data) => {
        setRows(Array.isArray(data) ? data : [])
        setError('')
      })
      .catch((err) => {
        setError(err.message || 'Could not load employees.')
      })
      .finally(() => {
        setLoading(false)
      })
  }

  useEffect(() => {
    loadEmployees()
  }, [])

  const deptList = useMemo(() => {
    const fromRows = Array.from(new Set(rows.map((r) => r.dept).filter(Boolean)))
    const base = ['Engineering', 'Marketing', 'Finance', 'Operations', 'Testing', 'Design', 'Support', 'HR', 'Sales']
    return ['All', ...Array.from(new Set([...base, ...fromRows]))]
  }, [rows])

  const filtered = useMemo(() => rows.filter((r) => {
    const nameStr = (r.name || '').toLowerCase()
    const idStr = String(r.id || '').toLowerCase()
    const qStr = q.toLowerCase()
    const okQ = nameStr.includes(qStr) || idStr.includes(qStr)
    const okD = dept === 'All' || r.dept === dept
    const level = r.burnout >= 70 ? 'High' : r.burnout >= 40 ? 'Moderate' : 'Low'
    const okR = risk === 'All' || risk === level
    return okQ && okD && okR
  }), [rows, q, dept, risk])
  const slice = filtered.slice(page * pageSize, page * pageSize + pageSize)

  if (loading && !rows.length) return <LoadingSkeleton rows={3} />
  if (error && !rows.length) return <ErrorState message={error} onRetry={loadEmployees} />

  return (
    <div className="card p-5 fade-in">
      <div className="mb-3 flex flex-wrap gap-2">
        <input value={q} onChange={(e) => { setQ(e.target.value); setPage(0) }} placeholder="Search employees..." className="ww-input mt-0 max-w-xs" />
        <select value={dept} onChange={(e) => { setDept(e.target.value); setPage(0) }} className="ww-input mt-0 max-w-[160px]">
          {deptList.map((d) => <option key={d}>{d}</option>)}
        </select>
        <select value={risk} onChange={(e) => { setRisk(e.target.value); setPage(0) }} className="ww-input mt-0 max-w-[160px]">
          <option>All</option><option>High</option><option>Moderate</option><option>Low</option>
        </select>
      </div>
      <DataTable
        onRowClick={setSel}
        columns={[
          { key: 'name', label: 'Employee', render: (r) => <span className="font-semibold text-slate-800 hover:text-[#0B4F6C] cursor-pointer">{r.name} <span className="text-xs text-slate-400 font-normal">{r.id}</span></span> },
          { key: 'dept', label: 'Department' },
          { key: 'role', label: 'Role' },
          { key: 'status', label: 'Status', render: (r) => <StatusBadge status={r.status} /> },
          { key: 'burnout', label: 'Burnout Risk', render: (r) => <span className="flex items-center gap-2">{r.burnout} <RiskBadge score={r.burnout} /></span> },
          { key: 'workload', label: 'Workload' },
          { key: 'lastCheckIn', label: 'Last Check-in' },
        ]}
        rows={slice}
      />
      <div className="mt-3 flex justify-end gap-2 text-sm">
        <button type="button" disabled={page === 0} onClick={() => setPage((p) => p - 1)} className="rounded border px-2 py-1 disabled:opacity-40">Prev</button>
        <button type="button" disabled={(page + 1) * pageSize >= filtered.length} onClick={() => setPage((p) => p + 1)} className="rounded border px-2 py-1 disabled:opacity-40">Next</button>
      </div>
      <EmployeeDetailDrawer
        open={!!sel}
        employeeId={sel?.raw_id || sel?.user_id || sel?.id}
        onClose={() => setSel(null)}
      />
    </div>
  )
}
