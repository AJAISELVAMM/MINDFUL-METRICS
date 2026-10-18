import { lazy } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import AppShell from './components/layout/AppShell'
import Login from './pages/Login'
import Landing from './pages/Landing'
import Unauthorized from './pages/Unauthorized'

// Employee pages (lazy-loaded)
const EmpDash = lazy(() => import('./pages/employee/Dashboard'))
const EmpAtt = lazy(() => import('./pages/employee/Attendance'))
const EmpLeave = lazy(() => import('./pages/employee/Leave'))
const EmpWork = lazy(() => import('./pages/employee/Work'))
const EmpBurn = lazy(() => import('./pages/employee/Burnout'))
const EmpTrends = lazy(() => import('./pages/employee/Trends'))
const EmpAsst = lazy(() => import('./pages/employee/Assistant'))
const EmpRec = lazy(() => import('./pages/employee/Recommendations'))
const EmpProf = lazy(() => import('./pages/employee/Profile'))
const EmpSet = lazy(() => import('./pages/employee/Settings'))

// Manager pages (lazy-loaded)
const MgrDash = lazy(() => import('./pages/manager/Dashboard'))
const MgrTeam = lazy(() => import('./pages/manager/Team'))
const MgrWork = lazy(() => import('./pages/manager/Workload'))
const MgrBurn = lazy(() => import('./pages/manager/Burnout'))
const MgrTrends = lazy(() => import('./pages/manager/Trends'))
const MgrWarn = lazy(() => import('./pages/manager/Warnings'))
const MgrProc = lazy(() => import('./pages/manager/WorkProcess'))
const MgrAsst = lazy(() => import('./pages/manager/Assistant'))
const MgrAtt = lazy(() => import('./pages/manager/Attendance'))
const MgrLeave = lazy(() => import('./pages/manager/LeaveRequests'))
const MgrPerm = lazy(() => import('./pages/manager/PermissionRequests'))
const MgrSet = lazy(() => import('./pages/manager/Settings'))

// HR pages (lazy-loaded)
const HrDash = lazy(() => import('./pages/hr/Dashboard'))
const HrEmp = lazy(() => import('./pages/hr/Employees'))
const HrDept = lazy(() => import('./pages/hr/Departments'))
const HrBurn = lazy(() => import('./pages/hr/Burnout'))
const HrWf = lazy(() => import('./pages/hr/Workforce'))
const HrRisk = lazy(() => import('./pages/hr/RiskMonitoring'))
const HrTrends = lazy(() => import('./pages/hr/Trends'))
const HrAtt = lazy(() => import('./pages/hr/Attendance'))
const HrLeave = lazy(() => import('./pages/hr/Leave'))
const HrTasks = lazy(() => import('./pages/hr/Tasks'))
const HrInt = lazy(() => import('./pages/hr/Interventions'))
const HrAsst = lazy(() => import('./pages/hr/Assistant'))
const HrModel = lazy(() => import('./pages/hr/ModelPerformance'))
const HrSet = lazy(() => import('./pages/hr/Settings'))
import { useAuth } from './hooks/useAuth'

function getGreeting(name, defaultRole) {
  const hour = new Date().getHours()
  const timeStr = hour < 12 ? 'Good Morning' : hour < 17 ? 'Good Afternoon' : 'Good Evening'
  const displayName = name ? name.split(' ')[0] : defaultRole
  return `${timeStr}, ${displayName}! ☀️`
}

function EmpLayout() {
  const { user } = useAuth()
  const path = useLocation().pathname
  return (
    <AppShell
      role="employee"
      title={path.endsWith('/dashboard') ? getGreeting(user?.name, 'Employee') : 'Mindful Metrics'}
      subtitle={path.endsWith('/dashboard') ? "Here's your overview for today." : undefined}
    />
  )
}

function MgrLayout() {
  const { user } = useAuth()
  const path = useLocation().pathname
  return (
    <AppShell
      role="manager"
      title={path.endsWith('/dashboard') ? getGreeting(user?.name, 'Manager') : 'Team wellbeing'}
      subtitle={path.endsWith('/dashboard') ? 'Support your team. Build a healthier workplace.' : undefined}
    />
  )
}

function HrLayout() {
  const { user } = useAuth()
  const path = useLocation().pathname
  return (
    <AppShell
      role="hr"
      title={path.endsWith('/dashboard') ? getGreeting(user?.name, 'HR Team') : 'Organization wellbeing'}
      subtitle={path.endsWith('/dashboard') ? 'People insights. Healthier organizations.' : undefined}
    />
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/unauthorized" element={<Unauthorized />} />

      <Route element={<EmpLayout />}>
        <Route path="/employee/dashboard" element={<EmpDash />} />
        <Route path="/employee/attendance" element={<EmpAtt />} />
        <Route path="/employee/leave" element={<EmpLeave />} />
        <Route path="/employee/check-in" element={<Navigate to="/employee/attendance" replace />} />
        <Route path="/employee/work" element={<EmpWork />} />
        <Route path="/employee/burnout" element={<EmpBurn />} />
        <Route path="/employee/trends" element={<EmpTrends />} />
        <Route path="/employee/assistant" element={<EmpAsst />} />
        <Route path="/employee/recommendations" element={<EmpRec />} />
        <Route path="/employee/profile" element={<EmpProf />} />
        <Route path="/employee/settings" element={<EmpSet />} />
      </Route>

      <Route element={<MgrLayout />}>
        <Route path="/manager/dashboard" element={<MgrDash />} />
        <Route path="/manager/my-attendance" element={<EmpAtt />} />
        <Route path="/manager/my-leave" element={<EmpLeave />} />
        <Route path="/manager/leave-requests" element={<MgrLeave />} />
        <Route path="/manager/permission-requests" element={<MgrPerm />} />
        <Route path="/manager/team" element={<MgrTeam />} />
        <Route path="/manager/workload" element={<MgrWork />} />
        <Route path="/manager/burnout" element={<MgrBurn />} />
        <Route path="/manager/trends" element={<MgrTrends />} />
        <Route path="/manager/warnings" element={<MgrWarn />} />
        <Route path="/manager/work-process" element={<MgrProc />} />
        <Route path="/manager/assistant" element={<MgrAsst />} />
        <Route path="/manager/attendance" element={<MgrAtt />} />
        <Route path="/manager/settings" element={<MgrSet />} />
      </Route>

      <Route element={<HrLayout />}>
        <Route path="/hr/dashboard" element={<HrDash />} />
        <Route path="/hr/employees" element={<HrEmp />} />
        <Route path="/hr/departments" element={<HrDept />} />
        <Route path="/hr/burnout" element={<HrBurn />} />
        <Route path="/hr/workforce" element={<HrWf />} />
        <Route path="/hr/risk-monitoring" element={<HrRisk />} />
        <Route path="/hr/trends" element={<HrTrends />} />
        <Route path="/hr/attendance" element={<HrAtt />} />
        <Route path="/hr/leave" element={<HrLeave />} />
        <Route path="/hr/tasks" element={<HrTasks />} />
        <Route path="/hr/interventions" element={<HrInt />} />
        <Route path="/hr/assistant" element={<HrAsst />} />
        <Route path="/hr/model-performance" element={<HrModel />} />
        <Route path="/hr/settings" element={<HrSet />} />
      </Route>

      <Route path="/" element={<Landing />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
