import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Users, AlertTriangle, Activity, ShieldCheck, ListChecks } from 'lucide-react'
import StatCard from '../../components/common/StatCard'
import ChartCard from '../../components/common/ChartCard'
import RiskBadge from '../../components/common/RiskBadge'
import RiskPie from '../../components/charts/RiskPie'
import BurnoutTrendChart from '../../components/charts/BurnoutTrendChart'
import WorkloadChart from '../../components/charts/WorkloadChart'
import TodayAttendanceCard from '../../components/common/TodayAttendanceCard'
import EmployeeDetailDrawer from '../../components/common/EmployeeDetailDrawer'
import { getTeamDashboard, getWorkData } from '../../services/api'
import LoadingSkeleton from '../../components/common/LoadingSkeleton'

export default function ManagerDashboard() {
  const [data, setData] = useState(null)
  const [hrTasks, setHrTasks] = useState([])
  const [showMyDrawer, setShowMyDrawer] = useState(false)
  const [selectedMember, setSelectedMember] = useState(null)
  const nav = useNavigate()

  useEffect(() => {
    loadAll()
    const handleRefresh = () => loadAll()
    window.addEventListener('mindful-metrics-refresh', handleRefresh)
    return () => window.removeEventListener('mindful-metrics-refresh', handleRefresh)
  }, [])

  async function loadAll() {
    try {
      const [dash, myWork] = await Promise.all([
        getTeamDashboard().catch(() => null),
        getWorkData().catch(() => null),
      ])
      setData(dash)
      setHrTasks(myWork?.tasks || [])
    } catch {
      /* ignore */
    }
  }

  if (!data) return <LoadingSkeleton />

  const members = data.members || []
  const high = members.filter((m) => m.status === 'High')
  const mod = members.filter((m) => m.status === 'Moderate')
  const total = data.totalMembers ?? members.length

  const avgHours = members.length
    ? (members.reduce((s, m) => s + (m.hours || 8.5), 0) / members.length).toFixed(1)
    : 8.5

  const hoursWeek = data?.hoursWeek || []
  const burnoutTrend7 = data?.burnoutTrend7 || []

  return (
    <div className="page-stack fade-in">
      {/* 1. Manager's Own Attendance Status Card */}
      <TodayAttendanceCard
        roleLabel="Manager"
        onAttendanceChange={loadAll}
        myBurnout={data?.my_burnout}
        onOpenDetails={() => setShowMyDrawer(true)}
      />

      {/* HR Organizational Directive Card (if assigned) */}
      {hrTasks.length > 0 && (
        <div className="card p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-l-4 border-l-blue-600 bg-white">
          <div>
            <div className="flex items-center gap-2">
              <span className="rounded bg-blue-100 text-blue-800 text-[11px] font-bold px-2 py-0.5">
                HR DIRECTIVE
              </span>
              <h4 className="text-sm font-semibold text-slate-800">
                {hrTasks[0].name || hrTasks[0].title}
              </h4>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Deadline: {hrTasks[0].deadline || 'Upcoming'} · Priority: {hrTasks[0].priority} · Progress: {hrTasks[0].progress || 0}%
            </p>
          </div>
          <button
            type="button"
            onClick={() => nav('/manager/work-process')}
            className="btn-primary text-xs whitespace-nowrap self-start sm:self-auto"
          >
            Manage HR Tasks ({hrTasks.length})
          </button>
        </div>
      )}

      {/* 2. 4 KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Total Members"
          value={total}
          icon={Users}
          tone="blue"
          hint="Engineering Team"
        />
        <StatCard
          label="High Risk"
          value={data.highRisk ?? high.length}
          hint="Needs attention"
          tone="high"
          icon={AlertTriangle}
        />
        <StatCard
          label="Moderate Risk"
          value={data.modRisk ?? mod.length}
          hint="Monitoring"
          tone="mod"
          icon={Activity}
        />
        <StatCard
          label="Low Risk"
          value={data.lowRisk ?? (total - high.length - mod.length)}
          hint="Healthy range"
          tone="low"
          icon={ShieldCheck}
        />
      </div>

      {/* 3. Charts Grid */}
      <div className="grid gap-4 lg:grid-cols-2">
        <ChartCard
          title="Team Burnout Risk Distribution"
          subtitle="Current team snapshot"
        >
          <RiskPie data={data.dist} centerValue={total} centerLabel="Members" />
        </ChartCard>

        <ChartCard
          title="Team Burnout Trend"
          filterText="Last 7 days"
        >
          <BurnoutTrendChart data={burnoutTrend7} />
        </ChartCard>

        <ChartCard
          title="Team Workload"
          filterText="This week"
        >
          <WorkloadChart data={hoursWeek} />
        </ChartCard>

        {/* Employees at Risk List */}
        <div className="card p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-[14px] font-bold text-[#0D192B]">Employees at Risk</h3>
              <span className="text-[11px] font-semibold text-[#64748B]">Sorted by score</span>
            </div>
            <div className="divide-y divide-[#E2EAF2]">
              {[...high, ...mod].slice(0, 4).map((m) => (
                <div
                  key={m.id}
                  onClick={() => setSelectedMember(m)}
                  className="flex items-center justify-between py-2.5 text-[13px] cursor-pointer hover:bg-slate-50/80 rounded px-1 -mx-1 transition-colors"
                >
                  <span className="font-semibold text-[#0D192B] hover:text-[#0B4F6C]">{m.name}</span>
                  <div className="flex items-center gap-3">
                    <span className="font-bold text-[#0D192B]">{m.burnout}</span>
                    <RiskBadge score={m.burnout} />
                  </div>
                </div>
              ))}
              {high.length === 0 && mod.length === 0 && (
                <p className="py-6 text-center text-[13px] text-[#94A3B8]">
                  All team members in healthy range
                </p>
              )}
            </div>
          </div>
          <p className="mt-3 text-[11px] text-[#94A3B8] border-t border-[#E2EAF2] pt-2">
            AI signals derived from attendance anomalies, task loads, and pulse surveys.
          </p>
        </div>
      </div>

      {/* Manager's Own Full Wellbeing & Burnout Details Drawer */}
      <EmployeeDetailDrawer
        open={showMyDrawer}
        employeeId={data?.manager?.id}
        onClose={() => setShowMyDrawer(false)}
      />

      {/* Selected Team Member Details Drawer */}
      <EmployeeDetailDrawer
        open={!!selectedMember}
        employeeId={selectedMember?.raw_id || selectedMember?.user_id || selectedMember?.id}
        onClose={() => setSelectedMember(null)}
      />
    </div>
  )
}
