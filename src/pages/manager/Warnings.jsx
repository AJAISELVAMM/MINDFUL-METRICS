import { useEffect, useState } from 'react'
import { getTeamDashboard } from '../../services/api'
import RiskBadge from '../../components/common/RiskBadge'
import EmptyState from '../../components/common/EmptyState'
import LoadingSkeleton from '../../components/common/LoadingSkeleton'

export default function Warnings() {
  const [warnings, setWarnings] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getTeamDashboard()
      .then((data) => setWarnings(data?.warnings || []))
      .catch(() => setWarnings([]))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <LoadingSkeleton rows={2} />
  if (!warnings.length) return <EmptyState title="No risk alerts. All team members are in stable range." />

  return (
    <div className="page-stack fade-in">
      <div className="card p-4 text-sm text-slate-700">
        {warnings.length} team member{warnings.length > 1 ? 's show' : ' shows'} elevated burnout-risk indicators based on multi-source AI fusion.
      </div>
      {warnings.map((w) => (
        <div key={w.id} className="card p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-semibold text-slate-800">
                {w.name} · <span className="text-xs text-slate-400">{w.id}</span>
              </p>
              <p className="text-xs text-slate-500">Change +{w.change} pts</p>
            </div>
            <RiskBadge score={w.current} />
          </div>
          <div className="mt-3 grid grid-cols-3 gap-3 text-sm">
            <div>
              <span className="text-xs text-slate-400">Current</span>
              <p className="font-semibold text-slate-800">{w.current}</p>
            </div>
            <div>
              <span className="text-xs text-slate-400">Previous</span>
              <p className="font-semibold text-slate-800">{w.previous}</p>
            </div>
            <div>
              <span className="text-xs text-slate-400">Associated Factors</span>
              <p className="text-xs text-slate-600">{(w.factors || []).join(' · ')}</p>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
