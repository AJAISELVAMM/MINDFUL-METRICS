import { useEffect, useState } from 'react'
import { Users, AlertTriangle, Activity, ShieldCheck, Sparkles } from 'lucide-react'
import StatCard from '../../components/common/StatCard'
import ChartCard from '../../components/common/ChartCard'
import RiskPie from '../../components/charts/RiskPie'
import DepartmentRiskChart from '../../components/charts/DepartmentRiskChart'
import BurnoutTrendChart from '../../components/charts/BurnoutTrendChart'
import { getHRDashboard } from '../../services/api'
import LoadingSkeleton from '../../components/common/LoadingSkeleton'

export default function HRDashboard() {
  const [data, setData] = useState(null)

  useEffect(() => {
    getHRDashboard().then(setData)
  }, [])

  if (!data) return <LoadingSkeleton />

  const total = data.totalEmployees || 0
  const high = data.highRisk || 0
  const mod = data.modRisk || 0
  const low = data.lowRisk || 0

  const trendData = (data.trend || []).map((t) => ({
    day: t.month,
    value: t.burnout,
  }))

  return (
    <div className="page-stack fade-in">
      {/* 4 KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Total Employees"
          value={total}
          icon={Users}
          tone="blue"
          hint="Organization Total"
        />
        <StatCard
          label="High Risk"
          value={high}
          hint="Needs Intervention"
          tone="high"
          icon={AlertTriangle}
        />
        <StatCard
          label="Moderate Risk"
          value={mod}
          hint="Under Monitoring"
          tone="mod"
          icon={Activity}
        />
        <StatCard
          label="Low Risk"
          value={low}
          hint="Healthy Balance"
          tone="low"
          icon={ShieldCheck}
        />
      </div>

      {/* Analytics Charts Grid */}
      <div className="grid gap-4 lg:grid-cols-2">
        <ChartCard
          title="Organization Risk Distribution"
          subtitle="Enterprise-wide breakdown"
        >
          <RiskPie data={data.dist} centerValue={total} centerLabel="Employees" />
        </ChartCard>

        <ChartCard
          title="Department Burnout Risk"
          subtitle="Department comparison"
        >
          <DepartmentRiskChart data={data.departments} />
        </ChartCard>

        <ChartCard
          title="Organization Trends"
          subtitle="6-Month trajectory"
        >
          <BurnoutTrendChart data={trendData} />
        </ChartCard>

        {/* HR Key Insights Card */}
        <div className="card p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Sparkles size={16} className="text-[#1E6BFF]" />
              <h3 className="text-[14px] font-bold text-[#0D192B]">Enterprise Key Insights</h3>
            </div>
            <div className="space-y-2.5 text-[13px] text-[#0D192B] leading-relaxed">
              <div className="flex items-start gap-2.5 rounded-xl bg-[#F8FAFC] p-3 border border-[#E2EAF2]">
                <span className="h-2 w-2 rounded-full bg-[#1E6BFF] mt-1.5 shrink-0" />
                <p className="text-[#64748B]">
                  Real-time organizational wellbeing derived from employee check-ins, tasks, and pulse surveys.
                </p>
              </div>
              <div className="flex items-start gap-2.5 rounded-xl bg-[#F8FAFC] p-3 border border-[#E2EAF2]">
                <span className="h-2 w-2 rounded-full bg-[#F59E0B] mt-1.5 shrink-0" />
                <p className="text-[#64748B]">
                  Engineering and Support show highest current project workload and overtime density.
                </p>
              </div>
              <div className="flex items-start gap-2.5 rounded-xl bg-[#F8FAFC] p-3 border border-[#E2EAF2]">
                <span className="h-2 w-2 rounded-full bg-[#10B981] mt-1.5 shrink-0" />
                <p className="text-[#64748B]">
                  Automated interventions recommended for {high} high-risk employees across 4 departments.
                </p>
              </div>
            </div>
          </div>
          <p className="mt-4 text-[11px] text-[#94A3B8] border-t border-[#E2EAF2] pt-2">
            Predictions computed by Mindful Metrics Random Forest ML pipeline (v1.0).
          </p>
        </div>
      </div>
    </div>
  )
}
