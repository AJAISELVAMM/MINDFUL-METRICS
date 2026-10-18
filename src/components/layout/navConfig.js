import {
  LayoutDashboard, CalendarDays, Palmtree, ClipboardCheck, Briefcase, Brain,
  TrendingUp, Bot, Lightbulb, User, Settings, Users, BarChart3, AlertTriangle,
  ListChecks, Building2, Activity, ShieldAlert, Handshake, FlaskConical, Clock,
} from 'lucide-react'

export const employeeNav = [
  { to: '/employee/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/employee/attendance', label: 'Attendance', icon: CalendarDays },
  { to: '/employee/leave', label: 'Leave', icon: Palmtree },
  { to: '/employee/work', label: 'My Work', icon: Briefcase },
  { to: '/employee/burnout', label: 'Burnout Analysis', icon: Brain },
  { to: '/employee/trends', label: 'My Trends', icon: TrendingUp },
  { to: '/employee/assistant', label: 'AI Assistant', icon: Bot },
  { to: '/employee/recommendations', label: 'Recommendations', icon: Lightbulb },
  { to: '/employee/profile', label: 'Profile', icon: User },
  { to: '/employee/settings', label: 'Settings', icon: Settings },
]

export const managerNav = [
  { to: '/manager/dashboard', label: 'Team Overview', icon: LayoutDashboard },
  { to: '/manager/my-attendance', label: 'My Attendance', icon: CalendarDays },
  { to: '/manager/my-leave', label: 'My Leave', icon: Palmtree },
  { to: '/manager/leave-requests', label: 'Leave Requests', icon: ClipboardCheck },
  { to: '/manager/permission-requests', label: 'Permission Requests', icon: Clock },
  { to: '/manager/team', label: 'My Team', icon: Users },
  { to: '/manager/attendance', label: 'Team Attendance', icon: Clock },
  { to: '/manager/workload', label: 'Team Workload', icon: BarChart3 },
  { to: '/manager/burnout', label: 'Burnout Analytics', icon: Brain },
  { to: '/manager/trends', label: 'Team Trends', icon: TrendingUp },
  { to: '/manager/warnings', label: 'Early Warnings', icon: AlertTriangle },
  { to: '/manager/work-process', label: 'Work Process', icon: ListChecks },
  { to: '/manager/assistant', label: 'AI Team Assistant', icon: Bot },
  { to: '/manager/settings', label: 'Settings', icon: Settings },
]

export const hrNav = [
  { to: '/hr/dashboard', label: 'Organization Overview', icon: LayoutDashboard },
  { to: '/hr/employees', label: 'Employees', icon: Users },
  { to: '/hr/departments', label: 'Departments', icon: Building2 },
  { to: '/hr/burnout', label: 'Burnout Analytics', icon: Brain },
  { to: '/hr/workforce', label: 'Workforce Analytics', icon: Activity },
  { to: '/hr/risk-monitoring', label: 'Risk Monitoring', icon: ShieldAlert },
  { to: '/hr/trends', label: 'Organization Trends', icon: TrendingUp },
  { to: '/hr/attendance', label: 'Attendance', icon: CalendarDays },
  { to: '/hr/leave', label: 'Leave Management', icon: Palmtree },
  { to: '/hr/tasks', label: 'Task Management', icon: ListChecks },
  { to: '/hr/interventions', label: 'Interventions', icon: Handshake },
  { to: '/hr/assistant', label: 'AI HR Assistant', icon: Bot },
  { to: '/hr/model-performance', label: 'Model Performance', icon: FlaskConical },
  { to: '/hr/settings', label: 'Settings', icon: Settings },
]
