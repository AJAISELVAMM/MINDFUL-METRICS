import { useEffect, useState, useMemo } from 'react'
import { getEmployees } from '../../services/api'
import RiskBadge from '../../components/common/RiskBadge'
import LoadingSkeleton from '../../components/common/LoadingSkeleton'
import ErrorState from '../../components/common/ErrorState'
import EmployeeDetailDrawer from '../../components/common/EmployeeDetailDrawer'

export default function RiskMonitoring() {
  const [employees, setEmployees] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [dept, setDept] = useState('All')
  const [level, setLevel] = useState('High')
  const [sel, setSel] = useState(null)

  function loadRiskData() {
    setLoading(true)
    setError('')
    getEmployees()
      .then((data) => {
        setEmployees(data || [])
        setError('')
      })
      .catch((err) => {
        setError(err.message || 'Could not load risk monitoring data.')
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadRiskData()
  }, [])

  const deptList = useMemo(() => {
    const fromRows = Array.from(new Set(employees.map((r) => r.dept).filter(Boolean)))
    const base = ['Engineering', 'Marketing', 'Finance', 'Operations', 'Testing', 'Design', 'Support', 'HR', 'Sales']
    return ['All', ...Array.from(new Set([...base, ...fromRows]))]
  }, [employees])

  if (loading && !employees.length) return <LoadingSkeleton rows={2} />
  if (error && !employees.length) return <ErrorState message={error} onRetry={loadRiskData} />

  const filtered = employees.filter((e) => {
    const l = e.burnout >= 70 ? 'High' : e.burnout >= 40 ? 'Moderate' : 'Low'
    return (dept === 'All' || e.dept === dept) && (level === 'All' || l === level)
  })

  return (
    <div className="page-stack fade-in">
      <div className="flex flex-wrap gap-2">
        <select value={dept} onChange={(e) => setDept(e.target.value)} className="ww-input mt-0 max-w-[160px]">
          {deptList.map((d) => (
            <option key={d}>{d}</option>
          ))}
        </select>
        <select value={level} onChange={(e) => setLevel(e.target.value)} className="ww-input mt-0 max-w-[160px]">
          <option>All</option>
          <option>High</option>
          <option>Moderate</option>
          <option>Low</option>
        </select>
      </div>
      <div className="card p-4 text-sm text-slate-700">
        AI Risk Early Warnings monitor correlated signals across attendance consistency, survey fatigue, and work volume.
      </div>
      {filtered.length ? (
        filtered.map((e) => (
          <div
            key={e.id}
            onClick={() => setSel(e)}
            className="card flex items-center justify-between p-4 cursor-pointer hover:border-[#0B4F6C]/40 transition-colors"
          >
            <div>
              <p className="font-semibold text-slate-800 hover:text-[#0B4F6C]">
                {e.name} · <span className="text-xs text-slate-400">{e.id}</span>
              </p>
              <p className="text-xs text-slate-500">
                {e.dept} · {e.role}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold">{e.burnout}</span>
              <RiskBadge score={e.burnout} />
            </div>
          </div>
        ))
      ) : (
        <div className="card p-6 text-center text-sm text-slate-400">
          No employees matching &apos;{level}&apos; risk in &apos;{dept}&apos;.
        </div>
      )}
      <EmployeeDetailDrawer
        open={!!sel}
        employeeId={sel?.raw_id || sel?.user_id || sel?.id}
        onClose={() => setSel(null)}
      />
    </div>
  )
}
