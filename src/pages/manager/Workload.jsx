import { useEffect, useState } from 'react'
import StatCard from '../../components/common/StatCard'
import ChartCard from '../../components/common/ChartCard'
import DataTable from '../../components/common/DataTable'
import WorkloadChart from '../../components/charts/WorkloadChart'
import { getTeamWorkload } from '../../services/api'
import LoadingSkeleton from '../../components/common/LoadingSkeleton'

export default function Workload() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getTeamWorkload()
      .then((d) => setData(d))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <LoadingSkeleton rows={2} />

  const summary = data?.summary || {
    assigned: 25,
    completed: 18,
    pending: 5,
    overdue: 2,
    avgWorkload: 64,
    avgHours: 9.1,
  }

  const rows = data?.members || []

  const hoursWeek = [
    { day: 'Mon', hours: 9.2, ot: 1.2 },
    { day: 'Tue', hours: 8.6, ot: 0.6 },
    { day: 'Wed', hours: 9.8, ot: 1.8 },
    { day: 'Thu', hours: 8.4, ot: 0.4 },
    { day: 'Fri', hours: 9.1, ot: 1.1 },
  ]

  return (
    <div className="page-stack fade-in">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-6">
        <StatCard label="Assigned" value={summary.assigned} />
        <StatCard label="Completed" value={summary.completed} tone="low" />
        <StatCard label="Pending" value={summary.pending} tone="mod" />
        <StatCard label="Overdue" value={summary.overdue} tone="high" />
        <StatCard label="Avg Workload" value={summary.avgWorkload} />
        <StatCard label="Avg Hours" value={summary.avgHours} />
      </div>
      <div className="grid gap-3 lg:grid-cols-2">
        <ChartCard title="Team Workload">
          <WorkloadChart data={hoursWeek} />
        </ChartCard>
        <ChartCard title="Overtime">
          <WorkloadChart data={hoursWeek.map((d) => ({ day: d.day, hours: d.ot }))} />
        </ChartCard>
      </div>
      <div className="card p-4">
        <DataTable
          columns={[
            { key: 'employee', label: 'Employee' },
            { key: 'assigned', label: 'Assigned' },
            { key: 'completed', label: 'Completed' },
            { key: 'pending', label: 'Pending' },
            { key: 'overdue', label: 'Overdue' },
            { key: 'workload', label: 'Workload' },
          ]}
          rows={rows}
        />
      </div>
    </div>
  )
}
