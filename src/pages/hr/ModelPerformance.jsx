import { useEffect, useState } from 'react'
import { getModelPerformance } from '../../services/api'
import DataTable from '../../components/common/DataTable'
import ChartCard from '../../components/common/ChartCard'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import LoadingSkeleton from '../../components/common/LoadingSkeleton'

export default function ModelPerformance() {
  const [data, setData] = useState(null)
  useEffect(() => { getModelPerformance().then(setData) }, [])
  if (!data) return <LoadingSkeleton rows={3} />
  const cells = (data.confusion || []).flat()
  return (
    <div className="page-stack fade-in">
      <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">{data.disclaimer}</div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <div className="card p-4 text-sm"><p className="text-[11px] text-[#6B7C93]">Model version</p><p className="font-semibold">{data.model_version || '—'}</p></div>
        <div className="card p-4 text-sm"><p className="text-[11px] text-[#6B7C93]">Dataset size</p><p className="font-semibold">{data.dataset_size || '—'}</p></div>
        <div className="card p-4 text-sm"><p className="text-[11px] text-[#6B7C93]">HIGH-class recall</p><p className="font-semibold">{data.recall_high != null ? Number(data.recall_high).toFixed(3) : '—'}</p></div>
        <div className="card p-4 text-sm"><p className="text-[11px] text-[#6B7C93]">Semantic backend</p><p className="font-semibold">{data.semantic_backend || '—'}</p></div>
      </div>
      <div className="card p-4">
        <h3 className="mb-3 text-sm font-semibold">Held-out comparison (computed)</h3>
        <DataTable
          columns={[
            { key: 'name', label: 'Model' },
            { key: 'accuracy', label: 'Accuracy', render: (r) => Number(r.accuracy).toFixed(3) },
            { key: 'precision', label: 'Precision', render: (r) => Number(r.precision).toFixed(3) },
            { key: 'recall', label: 'Recall', render: (r) => Number(r.recall).toFixed(3) },
            { key: 'f1', label: 'F1 Score', render: (r) => Number(r.f1).toFixed(3) },
          ]}
          rows={data.models || []}
        />
      </div>
      <ChartCard title="Feature importance (model-associated, not causal)">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data.features} layout="vertical" margin={{ left: 40 }}>
            <CartesianGrid stroke="#eef2f7" horizontal={false} />
            <XAxis type="number" />
            <YAxis type="category" dataKey="name" width={160} tick={{ fontSize: 11 }} />
            <Tooltip />
            <Bar dataKey="importance" fill="#1E6BFF" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>
      <div className="card p-4">
        <h3 className="mb-3 text-sm font-semibold">Confusion matrix (test set)</h3>
        <div className={`grid gap-2 text-center text-sm ${cells.length > 4 ? 'grid-cols-3 w-72' : 'grid-cols-2 w-56'}`}>
          {cells.map((n, i) => (
            <div key={i} className="rounded-lg bg-slate-50 py-6 font-semibold">{n}</div>
          ))}
        </div>
      </div>
    </div>
  )
}
