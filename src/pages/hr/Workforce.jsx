import { useEffect, useState } from 'react'
import StatCard from '../../components/common/StatCard'
import ChartCard from '../../components/common/ChartCard'
import AttendanceChart from '../../components/charts/AttendanceChart'
import { getDepartments, getEmployees } from '../../services/api'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import LoadingSkeleton from '../../components/common/LoadingSkeleton'
import ErrorState from '../../components/common/ErrorState'

export default function Workforce() {
  const [depts, setDepts] = useState([])
  const [employees, setEmployees] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  function loadWorkforce() {
    setLoading(true)
    setError('')
    Promise.all([getDepartments(), getEmployees()])
      .then(([d, e]) => {
        setDepts(d || [])
        setEmployees(e || [])
        setError('')
      })
      .catch((err) => {
        setError(err.message || 'Could not load workforce data.')
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadWorkforce()
  }, [])

  if (loading && !depts.length && !employees.length) return <LoadingSkeleton rows={2} />
  if (error && !depts.length && !employees.length) return <ErrorState message={error} onRetry={loadWorkforce} />

  const hoursWeek = [
    { day: 'Mon', hours: 9.1, ot: 1.1 },
    { day: 'Tue', hours: 8.8, ot: 0.8 },
    { day: 'Wed', hours: 9.3, ot: 1.3 },
    { day: 'Thu', hours: 8.9, ot: 0.9 },
    { day: 'Fri', hours: 8.6, ot: 0.6 },
  ]

  return (
    <div className="page-stack fade-in">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-6">
        <StatCard label="Avg Hours" value="9.0" />
        <StatCard label="Overtime" value="14%" tone="mod" />
        <StatCard label="Attendance" value="94%" tone="low" />
        <StatCard label="Task Completion" value="78%" />
        <StatCard label="Workforce Count" value={employees.length || 9} tone="blue" />
        <StatCard label="Leave rate" value="6%" />
      </div>
      <div className="grid gap-3 lg:grid-cols-2">
        <ChartCard title="Working Hours">
          <AttendanceChart data={hoursWeek} />
        </ChartCard>
        <ChartCard title="Workload Distribution">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={depts}>
              <CartesianGrid stroke="#eef2f7" vertical={false} />
              <XAxis dataKey="name" tick={{ fontSize: 10 }} />
              <YAxis width={24} />
              <Tooltip />
              <Bar dataKey="workload" fill="#60a5fa" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
    </div>
  )
}
