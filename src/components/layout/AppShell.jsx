import { Suspense, useState, useEffect } from 'react'
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { employeeNav, hrNav, managerNav } from './navConfig'
import Sidebar from './Sidebar'
import MobileSidebar from './MobileSidebar'
import Header from './Header'
import LoadingSkeleton from '../common/LoadingSkeleton'

const NAV = { employee: employeeNav, manager: managerNav, hr: hrNav }

export default function AppShell({ role, title, subtitle }) {
  const { user, ready } = useAuth()
  const [mobile, setMobile] = useState(false)
  const location = useLocation()

  useEffect(() => {
    if (location.pathname && !location.pathname.endsWith('/assistant')) {
      try {
        sessionStorage.setItem('mm_last_page', location.pathname)
      } catch {}
    }
  }, [location.pathname])

  if (!ready) return null
  if (!user) return <Navigate to="/login" replace />
  const userRole = (user.role || '').trim().toLowerCase()
  const expectedRole = (role || '').trim().toLowerCase()
  if (userRole !== expectedRole) return <Navigate to="/unauthorized" replace />

  const items = NAV[role]
  return (
    <div className="flex h-screen overflow-hidden bg-[#F0F5FA]">
      {/* Desktop Fixed Sidebar */}
      <Sidebar items={items} />

      {/* Mobile Sidebar Drawer */}
      <MobileSidebar open={mobile} items={items} onClose={() => setMobile(false)} />

      {/* Main Content Area - scrolls independently while sidebar stays stationary */}
      <div className="flex min-w-0 flex-1 flex-col lg:ml-[240px]">
        <Header title={title} subtitle={subtitle} onMenu={() => setMobile(true)} />
        <main className="min-h-0 min-w-0 flex-1 overflow-y-auto px-4 pb-10 md:px-8">
          <Suspense fallback={<LoadingSkeleton rows={3} />}>
            <Outlet />
          </Suspense>
        </main>
      </div>
    </div>
  )
}
