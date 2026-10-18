export default function StatCard({ label, value, hint, tone = 'blue', icon: Icon, subValue }) {
  const tones = {
    high: {
      text: 'text-[#EF4444]',
      bg: 'bg-[#FEF2F2]',
      border: 'border-[#FEE2E2]',
      stroke: '#EF4444',
      glow: 'rgba(239,68,68,0.15)',
    },
    mod: {
      text: 'text-[#F59E0B]',
      bg: 'bg-[#FFFBEB]',
      border: 'border-[#FEF3C7]',
      stroke: '#F59E0B',
      glow: 'rgba(245,158,11,0.15)',
    },
    low: {
      text: 'text-[#10B981]',
      bg: 'bg-[#ECFDF5]',
      border: 'border-[#D1FAE5]',
      stroke: '#10B981',
      glow: 'rgba(16,185,129,0.15)',
    },
    good: {
      text: 'text-[#10B981]',
      bg: 'bg-[#ECFDF5]',
      border: 'border-[#D1FAE5]',
      stroke: '#10B981',
      glow: 'rgba(16,185,129,0.15)',
    },
    blue: {
      text: 'text-[#1E6BFF]',
      bg: 'bg-[#EFF6FF]',
      border: 'border-[#DBEAFE]',
      stroke: '#1E6BFF',
      glow: 'rgba(30,107,255,0.15)',
    },
  }

  const activeTone = tones[tone] || tones.blue

  // Split value if it contains "/100" or similar
  let mainVal = value
  let denom = subValue || ''
  if (typeof value === 'string' && value.includes('/')) {
    const parts = value.split('/')
    mainVal = parts[0].trim()
    denom = `/${parts[1].trim()}`
  } else if (typeof value === 'number' && (label.toLowerCase().includes('score') || label.toLowerCase().includes('risk'))) {
    denom = '/100'
  }

  return (
    <div className="card p-4 sm:p-5 flex flex-col justify-between">
      {/* Top row: Label & Icon */}
      <div className="flex items-center justify-between gap-2">
        <p className="text-[13px] font-semibold text-[#64748B] tracking-tight">{label}</p>
        {Icon && (
          <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-[#EFF6FF] text-[#1E6BFF] shrink-0">
            <Icon size={16} strokeWidth={2} />
          </div>
        )}
      </div>

      {/* Middle row: Big Value + Sparkline */}
      <div className="mt-3 flex items-end justify-between gap-3">
        <div className="flex items-baseline gap-1">
          <span className="text-[26px] sm:text-[28px] font-bold text-[#0D192B] tracking-tight leading-none">
            {mainVal}
          </span>
          {denom && (
            <span className="text-[12px] font-semibold text-[#94A3B8]">
              {denom}
            </span>
          )}
        </div>

        {/* Mini Sparkline Curve or Mini Bars matching Reference Image 1 */}
        <div className="h-6 w-16 shrink-0 flex items-center justify-end">
          {tone === 'blue' ? (
            <div className="flex items-end gap-1 h-5">
              <span className="w-1 bg-[#1E6BFF] rounded-full h-2"></span>
              <span className="w-1 bg-[#1E6BFF] rounded-full h-3.5"></span>
              <span className="w-1 bg-[#1E6BFF] rounded-full h-5"></span>
              <span className="w-1 bg-[#1E6BFF] rounded-full h-4"></span>
              <span className="w-1 bg-[#1E6BFF] rounded-full h-3"></span>
            </div>
          ) : (
            <svg className="w-14 h-5 overflow-visible" viewBox="0 0 56 20" fill="none">
              <path
                d={
                  tone === 'high'
                    ? "M0 14 C 14 18, 28 6, 42 12 C 48 15, 52 8, 56 6"
                    : tone === 'mod'
                    ? "M0 12 C 14 14, 28 8, 42 13 C 48 15, 52 7, 56 5"
                    : "M0 15 C 14 12, 28 16, 42 8 C 48 4, 52 9, 56 4"
                }
                stroke={activeTone.stroke}
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          )}
        </div>
      </div>

      {/* Bottom row: Status Pill Badge */}
      {hint && (
        <div className="mt-2.5">
          <span
            className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-semibold border ${activeTone.bg} ${activeTone.text} ${activeTone.border}`}
          >
            {hint}
          </span>
        </div>
      )}
    </div>
  )
}
