import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ShieldAlert, Activity, Scale, Clock, Sparkles } from 'lucide-react'
import StatCard from '../../components/common/StatCard'
import ChartCard from '../../components/common/ChartCard'
import LoadingSkeleton from '../../components/common/LoadingSkeleton'
import BurnoutTrendChart from '../../components/charts/BurnoutTrendChart'
import WorkloadChart from '../../components/charts/WorkloadChart'
import AIInsightCard from '../../components/ai/AIInsightCard'
import TodayAttendanceCard from '../../components/common/TodayAttendanceCard'
import { getEmployeeDashboard } from '../../services/api'
import { useDay } from '../../context/DayContext'

export default function EmployeeDashboard() {
  const [data, setData] = useState(null)
  const nav = useNavigate()
  const day = useDay()

  useEffect(() => {
    loadData()
    const handleRefresh = () => loadData({ skipCache: true })
    window.addEventListener('mindful-metrics-refresh', handleRefresh)
    return () => window.removeEventListener('mindful-metrics-refresh', handleRefresh)
  }, [])

  function loadData(opts = {}) {
    getEmployeeDashboard(opts).then(setData)
  }

  if (!data) return <LoadingSkeleton />

  const kpis = data.kpis || {}

  // Determine burnout tone and hint
  const hasBurnout = kpis.burnoutRisk !== undefined && kpis.burnoutRisk !== null && kpis.burnoutRisk !== '—'
  const burnoutVal = hasBurnout ? kpis.burnoutRisk : 'N/A'
  const burnoutTone = hasBurnout ? (burnoutVal > 69 ? 'high' : burnoutVal > 39 ? 'mod' : 'good') : 'default'
  const burnoutHint = hasBurnout ? (burnoutVal > 69 ? 'High' : burnoutVal > 39 ? 'Moderate' : 'Good') : 'Unavailable'

  // Determine workload tone and hint
  const hasWorkload = kpis.workloadScore !== undefined && kpis.workloadScore !== null && kpis.workloadScore !== '—'
  const workloadVal = hasWorkload ? kpis.workloadScore : 'N/A'
  const workloadTone = hasWorkload ? (workloadVal > 69 ? 'high' : workloadVal > 39 ? 'mod' : 'good') : 'default'
  const workloadHint = hasWorkload ? (workloadVal > 69 ? 'High' : workloadVal > 39 ? 'Moderate' : 'Good') : 'Unavailable'

  // Determine wlb tone and hint
  const hasWlb = kpis.wlbScore !== undefined && kpis.wlbScore !== null && kpis.wlbScore !== '—'
  const wlbVal = hasWlb ? kpis.wlbScore : 'N/A'
  const wlbTone = hasWlb ? (wlbVal >= 70 ? 'good' : wlbVal >= 45 ? 'mod' : 'high') : 'default'
  const wlbHint = hasWlb ? (wlbVal >= 70 ? 'Good' : wlbVal >= 45 ? 'Moderate' : 'Needs Attention') : 'Unavailable'

  // Working hours
  const hoursVal = kpis.workingHours ? `${kpis.workingHours} hrs` : (day.workingHours || '—')

  return (
    <div className="page-stack fade-in">
      {/* 1. Today's Attendance Quick Action Card */}
      <TodayAttendanceCard onAttendanceChange={loadData} />

      {/* 2. Top Row: 4 KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Burnout Risk"
          value={burnoutVal}
          hint={burnoutHint}
          tone={burnoutTone}
          icon={ShieldAlert}
        />
        <StatCard
          label="Workload"
          value={workloadVal}
          hint={workloadHint}
          tone={workloadTone}
          icon={Activity}
        />
        <StatCard
          label="Work-Life Balance"
          value={wlbVal}
          hint={wlbHint}
          tone={wlbTone}
          icon={Scale}
        />
        <StatCard
          label="Working Hours"
          value={hoursVal}
          hint={day.phase === 'DAY_COMPLETED' ? 'Day completed' : 'This week avg'}
          tone="blue"
          icon={Clock}
        />
      </div>

      {/* 3. Middle Row: 2 Analytics Charts */}
      <div className="grid gap-4 lg:grid-cols-2">
        <ChartCard
          title="Burnout Risk Trend"
          filterText="Last 7 days"
        >
          <BurnoutTrendChart data={data.burnoutTrend7} />
        </ChartCard>

        <ChartCard
          title="Working Hours"
          filterText="This week"
        >
          <WorkloadChart data={data.hoursWeek} />
        </ChartCard>
      </div>

      {/* 4. Bottom Row: Today's Recommendation & Open AI Assistant CTA */}
      <div className="grid gap-4 md:grid-cols-[1fr_auto] items-stretch">
        <AIInsightCard
          title="Today's Recommendation"
          body="Try a 10-minute break to reduce stress."
          actionLabel="View Details"
          onAction={() => nav('/employee/recommendations')}
          iconType="bulb"
        />

        <div className="card p-5 flex items-center justify-center bg-white">
          <button
            type="button"
            onClick={() => nav('/employee/assistant')}
            className="btn-primary w-full md:w-auto px-7 py-3.5 rounded-2xl text-[14px] font-semibold shadow-[0_6px_20px_rgba(30,107,255,0.3)] hover:shadow-[0_8px_25px_rgba(30,107,255,0.4)]"
          >
            <Sparkles size={17} />
            <span>Open AI Assistant</span>
          </button>
        </div>
      </div>
    </div>
  )
}
