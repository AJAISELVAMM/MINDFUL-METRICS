import { ArrowRight, Lightbulb, Sparkles } from 'lucide-react'

export default function AIInsightCard({
  title = "Today's Recommendation",
  body = "Try a 10-minute break to reduce stress.",
  actionLabel = "View Details",
  onAction,
  iconType = 'bulb',
}) {
  const isSparkle = iconType === 'sparkle' || title.toLowerCase().includes('insight')

  return (
    <div className="card p-5 flex items-start gap-4">
      {/* Icon badge */}
      <div
        className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl ${
          isSparkle
            ? 'bg-[#EFF6FF] text-[#1E6BFF]'
            : 'bg-[#FFFBEB] text-[#D97706]'
        }`}
      >
        {isSparkle ? (
          <Sparkles size={20} strokeWidth={2} />
        ) : (
          <Lightbulb size={20} strokeWidth={2} />
        )}
      </div>

      {/* Content */}
      <div className="min-w-0 flex-1">
        <h4 className="text-[13px] font-bold text-[#0D192B] tracking-tight">{title}</h4>
        <p className="mt-1 text-[13px] leading-relaxed text-[#64748B] font-normal">{body}</p>
        {actionLabel && (
          <button
            type="button"
            onClick={onAction}
            className="mt-2.5 inline-flex items-center gap-1.5 text-[12px] font-semibold text-[#1E6BFF] hover:text-[#1558db] transition"
          >
            <span>{actionLabel}</span>
            <ArrowRight size={13} />
          </button>
        )}
      </div>
    </div>
  )
}
