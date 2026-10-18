import { useEffect, useMemo, useState } from 'react'
import DataTable from '../../components/common/DataTable'
import RiskBadge from '../../components/common/RiskBadge'
import EmployeeDetailDrawer from '../../components/common/EmployeeDetailDrawer'
import { getTeamMembers } from '../../services/api'

export default function Team() {
  const [rows, setRows] = useState([])
  const [q, setQ] = useState('')
  const [risk, setRisk] = useState('All')
  const [sel, setSel] = useState(null)

  useEffect(() => { getTeamMembers().then(setRows) }, [])
  const filtered = useMemo(() => rows.filter((r) => {
    const okQ = r.name.toLowerCase().includes(q.toLowerCase())
    const okR = risk === 'All' || r.status === risk
    return okQ && okR
  }), [rows, q, risk])

  return (
    <div className="card p-5 fade-in">
      <div className="mb-3 flex flex-wrap gap-2">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search employees..." className="ww-input mt-0 max-w-xs" />
        <select value={risk} onChange={(e) => setRisk(e.target.value)} className="ww-input mt-0 max-w-xs">
          <option>All</option><option>High</option><option>Moderate</option><option>Low</option>
        </select>
      </div>
      <DataTable
        onRowClick={setSel}
        columns={[
          { key: 'name', label: 'Employee', render: (r) => <span className="font-semibold text-slate-800 hover:text-[#0B4F6C] cursor-pointer">{r.name}</span> },
          { key: 'role', label: 'Role' },
          { key: 'workload', label: 'Workload' },
          { key: 'stress', label: 'Stress' },
          { key: 'burnout', label: 'Burnout Risk', render: (r) => <span className="flex items-center gap-2">{r.burnout} <RiskBadge score={r.burnout} /></span> },
          { key: 'hours', label: 'Working Hours' },
          { key: 'status', label: 'Status' },
        ]}
        rows={filtered}
      />
      <EmployeeDetailDrawer
        open={!!sel}
        employeeId={sel?.raw_id || sel?.user_id || sel?.id}
        onClose={() => setSel(null)}
      />
    </div>
  )
}
