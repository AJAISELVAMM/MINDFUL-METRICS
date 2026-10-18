import { NavLink } from 'react-router-dom'
import { Heart } from 'lucide-react'
import BrandLogo from '../common/BrandLogo'

export default function Sidebar({ items }) {
  return (
    <aside className="fixed inset-y-0 left-0 z-30 hidden h-screen w-[240px] shrink-0 flex-col overflow-y-auto bg-[#0B1727] text-slate-200 lg:flex shadow-[4px_0_24px_rgba(0,0,0,0.12)]">
      {/* Brand Header */}
      <div className="px-5 py-5 border-b border-white/[0.06]">
        <BrandLogo dark size={34} />
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
        {items.map((item) => {
          const Icon = item.icon
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-[13px] font-medium transition-all duration-150 ${
                  isActive
                    ? 'bg-[#1E6BFF] text-white shadow-[0_4px_14px_rgba(30,107,255,0.35)]'
                    : 'text-slate-300/75 hover:bg-white/[0.06] hover:text-white'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <Icon
                    size={17}
                    strokeWidth={isActive ? 2 : 1.75}
                    className={isActive ? 'text-white' : 'text-slate-400 group-hover:text-white'}
                  />
                  <span>{item.label}</span>
                </>
              )}
            </NavLink>
          )
        })}
      </nav>

      {/* Take Care Wellbeing Card */}
      <div className="p-3">
        <div className="rounded-2xl border border-white/[0.08] bg-white/[0.05] p-3.5 backdrop-blur-sm">
          <div className="mb-1 flex items-center gap-1.5 text-[12px] font-semibold text-white">
            <Heart size={14} className="text-rose-400 fill-rose-400/20" />
            <span>Take care</span>
          </div>
          <p className="text-[11px] leading-relaxed text-slate-300/60">
            A healthier you builds a stronger tomorrow.
          </p>
        </div>
      </div>
    </aside>
  )
}
