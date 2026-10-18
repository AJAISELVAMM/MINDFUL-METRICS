import { ChevronDown } from 'lucide-react'

export default function ChartCard({
  title,
  subtitle,
  children,
  filterText,
  action,
}) {
  return (
    <div className="card min-w-0 p-5 flex flex-col justify-between">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h3 className="text-[14px] font-bold text-[#0D192B] tracking-tight">{title}</h3>
          {subtitle && <p className="mt-0.5 text-[12px] text-[#64748B]">{subtitle}</p>}
        </div>

        {filterText ? (
          <div className="inline-flex items-center gap-1.5 rounded-xl border border-[#E2EAF2] bg-white px-2.5 py-1 text-[11px] font-semibold text-[#64748B] shadow-sm hover:border-[#CBD5E1] transition cursor-pointer">
            <span>{filterText}</span>
            <ChevronDown size={13} className="text-[#94A3B8]" />
          </div>
        ) : (
          action
        )}
      </div>

      <div className="h-[210px] min-w-0 w-full">{children}</div>
    </div>
  )
}
