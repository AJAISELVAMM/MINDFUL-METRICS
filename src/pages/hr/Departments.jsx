import { useEffect, useState } from 'react'
import ChartCard from '../../components/common/ChartCard'
import DepartmentRiskChart from '../../components/charts/DepartmentRiskChart'
import { getDepartments } from '../../services/api'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import LoadingSkeleton from '../../components/common/LoadingSkeleton'
import ErrorState from '../../components/common/ErrorState'

export default function Departments() {
  const [depts, setDepts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  function loadDepts() {
    setLoading(true)
    setError('')
    getDepartments()
      .then((d) => {
        setDepts(d || [])
        setError('')
      })
      .catch((err) => {
        setError(err.message || 'Could not load departments.')
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadDepts()
  }, [])

  if (loading && !depts.length) return <LoadingSkeleton rows={2} />
  if (error && !depts.length) return <ErrorState message={error} onRetry={loadDepts} />

  return (
    <div className="page-stack fade-in">
      <div className="grid gap-3 md:grid-cols-3">
        {depts.map((d) => (
          <div key={d.name} className="card p-4 text-sm">
            <p className="font-semibold text-slate-800">{d.name}</p>
            <p className="mt-2 text-xs text-slate-500">
              Burnout Risk {d.risk} · Workload {d.workload} · Stress {d.stress} · Overtime {d.overtime}%
            </p>
          </div>
        ))}
      </div>
      <div className="grid gap-3 lg:grid-cols-2">
        <ChartCard title="Department Burnout">
          <DepartmentRiskChart data={depts} />
        </ChartCard>
        <ChartCard title="Department Workload">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={depts}>
              <CartesianGrid stroke="#eef2f7" vertical={false} />
              <XAxis dataKey="name" tick={{ fontSize: 10 }} />
              <YAxis width={24} />
              <Tooltip />
              <Bar dataKey="workload" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
    </div>
  )
}
