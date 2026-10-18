import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'

export default function RiskPie({ data, centerValue, centerLabel }) {
  // Ensure we have high, moderate, low formatted
  const safeData = data || []
  const total = centerValue ?? safeData.reduce((s, d) => s + (d.value || 0), 0)

  // Map tones if fill not provided
  const palette = {
    High: '#EF4444',
    Moderate: '#F59E0B',
    Low: '#10B981',
  }

  return (
    <div className="flex h-full min-w-0 flex-col justify-between">
      {/* Donut Area */}
      <div className="relative min-h-[140px] flex-1">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={safeData}
              dataKey="value"
              nameKey="name"
              innerRadius={52}
              outerRadius={74}
              paddingAngle={3}
              stroke="#fff"
              strokeWidth={2}
            >
              {safeData.map((d) => (
                <Cell key={d.name} fill={d.fill || palette[d.name] || '#1E6BFF'} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                borderRadius: 12,
                border: '1px solid #E2EAF2',
                boxShadow: '0 8px 24px rgba(15,30,60,0.08)',
                fontSize: 12,
              }}
              formatter={(val, name) => [`${val} (${total ? Math.round((val / total) * 100) : 0}%)`, name]}
            />
          </PieChart>
        </ResponsiveContainer>

        {/* Center Total Count & Label */}
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <p className="text-[24px] font-bold text-[#0D192B] leading-none">{total}</p>
          <p className="text-[11px] font-medium text-[#64748B] mt-0.5">{centerLabel || 'Total'}</p>
        </div>
      </div>

      {/* Structured Legend with Dot, Label, Count, Percentage */}
      <div className="mt-2 grid grid-cols-3 gap-2 border-t border-[#E2EAF2] pt-3 text-[12px]">
        {safeData.map((d) => {
          const count = d.value || 0
          const pct = total ? Math.round((count / total) * 100) : 0
          const color = d.fill || palette[d.name] || '#1E6BFF'
          return (
            <div key={d.name} className="flex flex-col items-center sm:items-start text-center sm:text-left">
              <div className="inline-flex items-center gap-1.5 font-medium text-[#64748B]">
                <span className="h-2.5 w-2.5 rounded-full shrink-0" style={{ backgroundColor: color }} />
                <span>{d.name}</span>
              </div>
              <div className="mt-0.5 flex items-baseline gap-1 text-[13px] font-bold text-[#0D192B]">
                <span>{count}</span>
                <span className="text-[11px] font-normal text-[#94A3B8]">({pct}%)</span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
