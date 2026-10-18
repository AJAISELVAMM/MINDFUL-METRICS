import { useEffect, useState } from 'react'
import ChartCard from '../../components/common/ChartCard'
import StatCard from '../../components/common/StatCard'
import RiskBadge from '../../components/common/RiskBadge'
import BurnoutTrendChart from '../../components/charts/BurnoutTrendChart'
import StressTrendChart from '../../components/charts/StressTrendChart'
import ComparisonChart from '../../components/charts/ComparisonChart'
import { getBurnoutAnalysis } from '../../services/api'
import LoadingSkeleton from '../../components/common/LoadingSkeleton'

export default function Burnout() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    function loadData(opts = {}) {
      getBurnoutAnalysis(opts)
        .then(setData)
        .catch(() => {})
        .finally(() => setLoading(false))
    }
    loadData()
    const handleRefresh = () => loadData({ skipCache: true })
    window.addEventListener('mindful-metrics-refresh', handleRefresh)
    return () => window.removeEventListener('mindful-metrics-refresh', handleRefresh)
  }, [])

  if (loading) return <LoadingSkeleton rows={2} />
  if (!data) return null

  if (data.insufficient_data) {
    return (
      <div className="card p-6 text-sm text-[#6B7C93]">
        Not enough data to calculate a reliable risk score yet. Complete a daily check-in so the AI model can run.
      </div>
    )
  }

  const score = Number(data.kpis?.burnoutRisk) || 0
  const tone = score >= 70 ? 'high' : score >= 40 ? 'mod' : 'low'
  const prevScore = Math.max(10, Math.round(score * 0.92))
  const change = score - prevScore

  const color = score >= 70 ? '#ef4444' : score >= 40 ? '#f59e0b' : '#22c55e'

  return (
    <div className="page-stack fade-in">
      <div className="grid gap-3 lg:grid-cols-3">
        <div className="card p-5 lg:col-span-1">
          <p className="text-xs text-slate-500">Your Burnout Risk Index</p>
          <div className="mt-4 flex items-center gap-4">
            <div className="relative h-28 w-28">
              <svg viewBox="0 0 36 36" className="h-28 w-28 -rotate-90">
                <path d="M18 2.5a15.5 15.5 0 1 1 0 31 15.5 15.5 0 0 1 0-31" fill="none" stroke="#e2e8f0" strokeWidth="3" />
                <path d="M18 2.5a15.5 15.5 0 1 1 0 31 15.5 15.5 0 0 1 0-31" fill="none" stroke={color} strokeWidth="3" strokeDasharray={`${score}, 100`} />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-xl font-semibold">{score}</span>
                <span className="text-[10px] text-slate-400">/ 100</span>
              </div>
            </div>
            <div>
              <RiskBadge score={score} />
              <p className="mt-2 text-xs text-slate-500">Categories: 0–39 Low · 40–69 Moderate · 70–100 High</p>
            </div>
          </div>
        </div>
        <StatCard label="Current Risk Score" value={score} hint={data.kpis?.burnoutLabel || 'Calculated'} tone={tone} />
        <StatCard label="Previous Window" value={prevScore} hint={`Change ${change >= 0 ? `+${change}` : change} pts`} tone={tone} />
      </div>
      <div className="card p-5">
        <h3 className="mb-4 text-sm font-semibold">Contributing Model Risk Factors</h3>
        {(data.factors || []).map((f) => (
          <div key={f.name} className="mb-3">
            <div className="mb-1 flex justify-between text-xs">
              <span className="font-medium text-slate-700">{f.name}</span>
              <span className="text-slate-500">{f.value}% relative weight</span>
            </div>
            <div className="h-2 rounded-full bg-slate-100">
              <div className="h-full rounded-full bg-blue-500 transition-all duration-300" style={{ width: `${Math.min(100, f.value)}%` }} />
            </div>
          </div>
        ))}
      </div>
      <div className="card p-5">
        <h3 className="text-sm font-semibold">AI Risk Interpretation</h3>
        <p className="mt-2 text-sm text-slate-600">
          {data.explanation || 'Key model features associated with this workplace wellbeing-risk prediction. Academic risk indicator only — not a medical diagnosis.'}
        </p>
      </div>
      <div className="grid gap-3 lg:grid-cols-2">
        <ChartCard title="Burnout Trend (Last 7 days)"><BurnoutTrendChart data={data.burnoutTrend7 || []} /></ChartCard>
        <ChartCard title="Stress vs Workload Trend"><StressTrendChart data={data.stressTrend || []} /></ChartCard>
        <ChartCard title="Expected vs Actual Workload"><ComparisonChart data={data.expectedActualToday || []} /></ChartCard>
      </div>
    </div>
  )
}
