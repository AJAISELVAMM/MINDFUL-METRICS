import { useState } from 'react'
import ChartCard from '../../components/common/ChartCard'
import BurnoutTrendChart from '../../components/charts/BurnoutTrendChart'
import StressTrendChart from '../../components/charts/StressTrendChart'
import WorkloadChart from '../../components/charts/WorkloadChart'
import ComparisonChart from '../../components/charts/ComparisonChart'
import { burnoutTrend7, hoursWeek, stressTrend, expectedActualToday, communicationSentiment } from '../../data/chartData'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

const filters = ['7 Days', '30 Days', '3 Months']

export default function Trends() {
  const [f, setF] = useState('7 Days')
  const count = f === '7 Days' ? 7 : f === '30 Days' ? 30 : 90
  const expand = (data) => Array.from({ length: count }, (_, i) => ({ ...data[i % data.length], day: `${i + 1}` }))
  return (
    <div className="page-stack fade-in">
      <div className="flex gap-2">
        {filters.map((x) => (
          <button key={x} type="button" onClick={() => setF(x)} className={`rounded-full px-3 py-1 text-xs font-medium ${f === x ? 'bg-blue-600 text-white' : 'bg-white border border-slate-200 text-slate-600'}`}>{x}</button>
        ))}
      </div>
      <div className="grid gap-3 lg:grid-cols-2">
        <ChartCard title="Burnout Risk"><BurnoutTrendChart data={expand(burnoutTrend7)} /></ChartCard>
        <ChartCard title="Stress"><StressTrendChart data={expand(stressTrend)} /></ChartCard>
        <ChartCard title="Working Hours"><WorkloadChart data={expand(hoursWeek)} /></ChartCard>
        <ChartCard title="Expected vs Actual Workload"><ComparisonChart data={expectedActualToday} /></ChartCard>
        <ChartCard title="Expected vs Actual Stress"><ComparisonChart data={expectedActualToday.filter((d) => d.metric !== 'Difficulty')} /></ChartCard>
        <ChartCard title="Communication Sentiment" subtitle="Aggregated indicators only">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={communicationSentiment}>
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
