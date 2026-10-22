import { useEffect, useState } from 'react'
import StatCard from '../../components/common/StatCard'
import ChartCard from '../../components/common/ChartCard'
import RiskPie from '../../components/charts/RiskPie'
import BurnoutTrendChart from '../../components/charts/BurnoutTrendChart'
import StressTrendChart from '../../components/charts/StressTrendChart'
import ComparisonChart from '../../components/charts/ComparisonChart'
import { getTeamDashboard } from '../../services/api'
import { stressTrend, expectedActualToday, communicationSentiment } from '../../data/chartData'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import LoadingSkeleton from '../../components/common/LoadingSkeleton'

export default function ManagerBurnout() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getTeamDashboard()
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <LoadingSkeleton rows={2} />

  const members = data?.members || []
  const avgBurnout = members.length
    ? Math.round(members.reduce((s, m) => s + (m.burnout || 50), 0) / members.length)
    : 58

  const high = data?.highRisk ?? members.filter((m) => m.status === 'High').length
  const mod = data?.modRisk ?? members.filter((m) => m.status === 'Moderate').length
  const warnings = data?.warnings?.length || high

  const burnoutTrend7 = data?.burnoutTrend7 || []
  const sTrend = data?.stressTrend || stressTrend
  const eaData = data?.expectedActualToday || expectedActualToday
  const commSent = data?.communicationSentiment || communicationSentiment

  const dist = data?.dist || [
    { name: 'High', value: high, fill: '#ef4444' },
    { name: 'Moderate', value: mod, fill: '#f59e0b' },
    { name: 'Low', value: Math.max(1, members.length - high - mod), fill: '#22c55e' },
  ]

  return (
    <div className="page-stack fade-in">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatCard label="Average Team Burnout" value={avgBurnout} tone={avgBurnout >= 65 ? 'high' : avgBurnout >= 45 ? 'mod' : 'low'} />
        <StatCard label="High Risk" value={high} tone="high" />
        <StatCard label="Moderate Risk" value={mod} tone="mod" />
        <StatCard label="Early Warnings" value={warnings} tone={warnings > 0 ? 'high' : 'low'} />
      </div>
      <div className="grid gap-3 lg:grid-cols-2">
        <ChartCard title="Risk Distribution">
          <RiskPie data={dist} centerValue={members.length || 7} centerLabel="Members" />
        </ChartCard>
        <ChartCard title="Burnout Trend">
          <BurnoutTrendChart data={burnoutTrend7} />
        </ChartCard>
        <ChartCard title="Stress Trend">
          <StressTrendChart data={sTrend} />
        </ChartCard>
        <ChartCard title="Expected vs Actual Workload">
          <ComparisonChart data={eaData} />
        </ChartCard>
        <ChartCard title="Communication Sentiment" subtitle="Aggregated team indicators (privacy-preserved)">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={commSent}>
              <CartesianGrid stroke="#eef2f7" vertical={false} />
              <XAxis dataKey="week" tick={{ fontSize: 11 }} />
              <YAxis width={24} />
              <Tooltip />
              <Area dataKey="negative" fill="#fee2e2" stroke="#ef4444" />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
    </div>
  )
}
