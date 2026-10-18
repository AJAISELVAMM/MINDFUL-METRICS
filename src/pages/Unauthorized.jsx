import { Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

export default function Unauthorized() {
  const { user } = useAuth()
  const home = user?.role === 'manager' ? '/manager/dashboard' : user?.role === 'hr' ? '/hr/dashboard' : '/employee/dashboard'
  return (
    <div className="flex min-h-screen items-center justify-center bg-[#EEF5FA] p-6">
      <div className="card max-w-md p-8 text-center">
        <h1 className="text-[18px] font-semibold text-[#172B4D]">Access restricted</h1>
        <p className="mt-2 text-[13px] text-[#6B7C93]">This area is not available for your demo role.</p>
        <Link to={home} className="btn-primary mt-4 inline-block">Go to my dashboard</Link>
      </div>
    </div>
  )
}
