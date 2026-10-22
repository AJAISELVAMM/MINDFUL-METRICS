import { useState, useEffect } from 'react'
import ChartCard from '../../components/common/ChartCard'
import BurnoutTrendChart from '../../components/charts/BurnoutTrendChart'
import StressTrendChart from '../../components/charts/StressTrendChart'
import WorkloadChart from '../../components/charts/WorkloadChart'
import ComparisonChart from '../../components/charts/ComparisonChart'
import { getEmployeeTrends } from '../../services/api'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import LoadingSkeleton from '../../components/common/LoadingSkeleton'

const filters = ['7 Days', '30 Days', '3 Months']

export default function Trends() {
  const [f, setF] = useState('7 Days')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getEmployeeTrends()
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <LoadingSkeleton rows={2} />

  const count = f === '7 Days' ? 7 : f === '30 Days' ? 30 : 90
  const expand = (list) => {
    if (!list || !list.length) return []
    if (f === '7 Days') return list
    return Array.from({ length: count }, (_, i) => ({ ...list[i % list.length], day: `${i + 1}` }))
  }

  const burnoutData = data?.burnoutTrend7 || []
  const stressData = data?.stressTrend || []
  const hoursData = data?.hoursWeek || []
  const eaData = data?.expectedActualToday || []
  const commSent = data?.communicationSentiment || []

  return (
    <div className="page-stack fade-in">
      <div className="flex gap-2">
        {filters.map((x) => (
          <button key={x} type="button" onClick={() => setF(x)} className={`rounded-full px-3 py-1 text-xs font-medium ${f === x ? 'bg-blue-600 text-white' : 'bg-white border border-slate-200 text-slate-600'}`}>{x}</button>
        ))}
      </div>
      <div className="grid gap-3 lg:grid-cols-2">
        <ChartCard title="Burnout Risk"><BurnoutTrendChart data={expand(burnoutData)} /></ChartCard>
        <ChartCard title="Stress"><StressTrendChart data={expand(stressData)} /></ChartCard>
        <ChartCard title="Working Hours"><WorkloadChart data={expand(hoursData)} /></ChartCard>
        <ChartCard title="Expected vs Actual Workload"><ComparisonChart data={eaData} /></ChartCard>
        <ChartCard title="Expected vs Actual Stress"><ComparisonChart data={eaData.filter((d) => d.metric !== 'Difficulty')} /></ChartCard>
        <ChartCard title="Communication Sentiment" subtitle="Aggregated indicators only">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={commSent}>
              <CartesianGrid stroke="#eef2f7" vertical={false} />
              <XAxis dataKey="week" tick={{ fontSize: 11 }} />
              <YAxis width={28} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Area dataKey="positive" stroke="#22c55e" fill="#dcfce7" />
              <Area dataKey="negative" stroke="#ef4444" fill="#fee2e2" />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
    </div>
  )
}
