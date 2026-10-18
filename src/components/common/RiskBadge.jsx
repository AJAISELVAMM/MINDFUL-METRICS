export function riskLevel(score) {
  if (score <= 39) return 'Low'
  if (score <= 69) return 'Moderate'
  return 'High'
}

export function riskColor(level) {
  if (level === 'High') return 'bg-[#FEF2F2] text-[#EF4444] border-[#FEE2E2]'
  if (level === 'Moderate') return 'bg-[#FFFBEB] text-[#F59E0B] border-[#FEF3C7]'
  return 'bg-[#ECFDF5] text-[#10B981] border-[#D1FAE5]'
}

export default function RiskBadge({ score, level }) {
  const l = level || riskLevel(score)
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wider ${riskColor(
        l
      )}`}
    >
      {l}
    </span>
  )
}
