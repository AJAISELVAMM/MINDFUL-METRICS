export default function RecommendationCard({ category, body, icon: Icon, onAction }) {
  return (
    <div className="card p-5">
      <div className="mb-2 flex items-center gap-2">
        {Icon && (
          <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-[#EFF6FF] text-[#1E6BFF]">
            <Icon size={16} />
          </span>
        )}
        <p className="text-[12px] font-bold uppercase tracking-wider text-[#64748B]">{category}</p>
      </div>
      <p className="text-[14px] leading-relaxed text-[#0D192B]">{body}</p>
      <button type="button" onClick={onAction} className="btn-secondary mt-4">View action</button>
    </div>
  )
}
