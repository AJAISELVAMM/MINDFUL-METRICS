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
    assigned: 0,
    completed: 0,
    pending: 0,
    overdue: 0,
    avgWorkload: 0,
    avgHours: 0,
  }

  const rows = data?.members || []
  const hoursWeek = data?.hoursWeek || []

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
