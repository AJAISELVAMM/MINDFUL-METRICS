import { Menu } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import NotificationDropdown from '../common/NotificationDropdown'

export default function Header({ title, subtitle, onMenu }) {
  const { user, logout } = useAuth()
  const nav = useNavigate()
  const [open, setOpen] = useState(false)

  // Format date like "Thu, 1 Oct 2026"
  const dateStr = new Date().toLocaleDateString('en-GB', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })

  const initials = (user?.name || 'User')
    .split(' ')
    .filter(Boolean)
    .map((p) => p[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()

  return (
    <header className="sticky top-0 z-20 flex items-center justify-between gap-4 px-4 py-4 md:px-8 bg-[#F0F5FA]/90 backdrop-blur-md">
      <div className="flex min-w-0 items-center gap-3">
        <button
          type="button"
          className="rounded-xl border border-[#E2EAF2] bg-white p-2.5 text-[#0D192B] shadow-sm lg:hidden hover:bg-slate-50 transition"
          onClick={onMenu}
          aria-label="Open menu"
        >
          <Menu size={18} />
        </button>
        <div className="min-w-0">
          <h1 className="text-[20px] md:text-[22px] font-bold tracking-tight text-[#0D192B] leading-tight">
            {title}
          </h1>
          {subtitle && (
            <p className="mt-0.5 text-[12px] md:text-[13px] text-[#64748B] font-normal">
              {subtitle}
            </p>
          )}
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-2.5 md:gap-3">
        <div className="hidden items-center rounded-xl border border-[#E2EAF2] bg-white px-3.5 py-1.5 text-[12px] font-medium text-[#64748B] shadow-sm sm:flex">
          {dateStr}
        </div>

        <NotificationDropdown />

        <div className="relative">
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className="flex h-9 w-9 items-center justify-center rounded-full bg-[#0B1727] text-[11px] font-bold text-white shadow-sm ring-2 ring-white hover:ring-[#1E6BFF]/30 transition overflow-hidden"
            aria-label="Profile menu"
          >
            {user?.avatar ? (
              <img src={user.avatar} alt={user?.name || 'User'} className="h-full w-full object-cover" />
            ) : (
              initials || 'U'
            )}
          </button>
          {open && (
            <div className="absolute right-0 z-30 mt-2 w-48 rounded-2xl border border-[#E2EAF2] bg-white p-2 shadow-[0_12px_36px_rgba(15,30,60,0.12)]">
              <div className="px-3 py-2 border-b border-[#E2EAF2]/60">
                <p className="text-[13px] font-semibold text-[#0D192B] truncate">{user?.name || 'User'}</p>
                <p className="text-[11px] text-[#64748B] truncate">{user?.email}</p>
              </div>
              <button
                type="button"
                className="w-full mt-1 rounded-xl px-3 py-2 text-left text-[12px] font-medium text-rose-600 hover:bg-rose-50 transition"
                onClick={() => {
                  setOpen(false)
                  logout()
                  nav('/login')
                }}
              >
                Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
