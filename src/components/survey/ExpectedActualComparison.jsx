export default function ExpectedActualComparison({ items }) {
  return (
    <div className="space-y-3">
      {items.map((it) => {
        const diff = it.actual - it.expected
        return (
          <div key={it.metric} className="rounded-lg border border-slate-100 p-3">
            <div className="mb-2 flex items-center justify-between text-sm">
              <span className="font-medium text-slate-700">{it.metric}</span>
              <span className={`text-xs font-semibold ${diff > 0 ? 'text-red-500' : 'text-emerald-600'}`}>
                {diff > 0 ? `+${diff}` : diff}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-3 text-xs text-slate-500">
              <div>
                Expected
                <div className="mt-1 h-2 overflow-hidden rounded-full bg-slate-100">
                  <div className="h-full rounded-full bg-blue-200" style={{ width: `${(it.expected / 5) * 100}%` }} />
                </div>
                <p className="mt-1 font-medium text-slate-700">{it.expected} / 5</p>
              </div>
              <div>
                Actual
                <div className="mt-1 h-2 overflow-hidden rounded-full bg-slate-100">
                  <div className="h-full rounded-full bg-blue-600" style={{ width: `${(it.actual / 5) * 100}%` }} />
                </div>
                <p className="mt-1 font-medium text-slate-700">{it.actual} / 5</p>
              </div>
            </div>
          </div>
        )
      })}
      <p className="text-sm text-slate-600">Today&apos;s actual workload was significantly higher than expected.</p>
    </div>
  )
}
