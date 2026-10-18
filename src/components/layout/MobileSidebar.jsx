import { NavLink } from 'react-router-dom'
import { Heart, X } from 'lucide-react'
import BrandLogo from '../common/BrandLogo'

export default function MobileSidebar({ open, items, onClose }) {
  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 lg:hidden">
      {/* Backdrop */}
      <button
        type="button"
        className="absolute inset-0 bg-[#0B1727]/60 backdrop-blur-sm transition-opacity"
        aria-label="Close menu"
        onClick={onClose}
      />

      {/* Drawer */}
      <aside className="absolute left-0 top-0 h-full w-[260px] overflow-y-auto bg-[#0B1727] p-4 text-slate-200 shadow-2xl flex flex-col fade-in">
        <div className="flex items-center justify-between pb-4 border-b border-white/[0.08]">
          <BrandLogo dark size={32} />
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-white/[0.08]"
            aria-label="Close sidebar"
          >
            <X size={18} />
          </button>
        </div>

        <nav className="flex-1 space-y-1 overflow-y-auto py-3">
          {items.map((item) => {
            const Icon = item.icon
            return (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={onClose}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-[13px] font-medium transition-all ${
                    isActive
                      ? 'bg-[#1E6BFF] text-white shadow-[0_4px_14px_rgba(30,107,255,0.35)]'
                      : 'text-slate-300/75 hover:bg-white/[0.06] hover:text-white'
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <Icon size={17} strokeWidth={isActive ? 2 : 1.75} />
                    <span>{item.label}</span>
                  </>
                )}
              </NavLink>
            )
          })}
        </nav>

        <div className="pt-2">
          <div className="rounded-2xl border border-white/[0.08] bg-white/[0.05] p-3">
            <div className="mb-1 flex items-center gap-1.5 text-[12px] font-semibold text-white">
              <Heart size={14} className="text-rose-400 fill-rose-400/20" />
              <span>Take care</span>
            </div>
            <p className="text-[11px] text-slate-300/60 leading-relaxed">
              A healthier you builds a stronger tomorrow.
            </p>
          </div>
        </div>
      </aside>
    </div>
  )
}
