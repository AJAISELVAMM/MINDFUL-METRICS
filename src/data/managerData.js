export const managerProfile = {
  name: 'Priya Nair',
  firstName: 'Priya',
  email: 'manager@mindfulmetrics.com',
  role: 'Engineering Manager',
  department: 'Engineering',
}

export const teamMembers = [
  { id: 'E102', name: 'Rahul Sharma', role: 'Senior Engineer', workload: 88, stress: 84, burnout: 86, hours: 10.4, status: 'High', dept: 'Engineering' },
  { id: 'E109', name: 'Anita Krishnan', role: 'Engineer', workload: 80, stress: 76, burnout: 78, hours: 9.8, status: 'High', dept: 'Engineering' },
  { id: 'E121', name: 'Vikram Rao', role: 'Engineer', workload: 70, stress: 64, burnout: 66, hours: 9.1, status: 'Moderate', dept: 'Engineering' },
  { id: 'E130', name: 'Sneha Reddy', role: 'QA Engineer', workload: 68, stress: 60, burnout: 62, hours: 8.9, status: 'Moderate', dept: 'Testing' },
  { id: 'E118', name: 'Arjun Mehta', role: 'Software Engineer', workload: 61, stress: 68, burnout: 72, hours: 9.2, status: 'High', dept: 'Engineering' },
  { id: 'E141', name: 'Karthik Iyer', role: 'Frontend Engineer', workload: 55, stress: 48, burnout: 44, hours: 8.4, status: 'Low', dept: 'Engineering' },
  { id: 'E150', name: 'Meera Joshi', role: 'Backend Engineer', workload: 52, stress: 46, burnout: 41, hours: 8.2, status: 'Low', dept: 'Engineering' },
  { id: 'E155', name: 'Farhan Ali', role: 'DevOps Engineer', workload: 58, stress: 51, burnout: 49, hours: 8.6, status: 'Low', dept: 'Engineering' },
]

export const earlyWarnings = [
  { id: 'E102', name: 'Rahul Sharma', current: 86, previous: 62, change: 24, factors: ['Workload ↑', 'Stress ↑', 'Overtime ↑'] },
  { id: 'E109', name: 'Anita Krishnan', current: 78, previous: 61, change: 17, factors: ['Workload ↑', 'Deadline pressure ↑'] },
  { id: 'E118', name: 'Arjun Mehta', current: 72, previous: 64, change: 8, factors: ['Stress ↑', 'Hours ↑'] },
  { id: 'E121', name: 'Vikram Rao', current: 66, previous: 58, change: 8, factors: ['Overtime ↑'] },
]

export const teamAttendance = [
  { name: 'Rahul Sharma', status: 'Present', checkIn: '09:04 AM', checkOut: '—', hours: '—' },
  { name: 'Anita Krishnan', status: 'Present', checkIn: '09:18 AM', checkOut: '—', hours: '—' },
  { name: 'Vikram Rao', status: 'Late', checkIn: '09:46 AM', checkOut: '—', hours: '—' },
  { name: 'Sneha Reddy', status: 'On Leave', checkIn: '—', checkOut: '—', hours: '—' },
  { name: 'Arjun Mehta', status: 'Present', checkIn: '09:12 AM', checkOut: '—', hours: '—' },
  { name: 'Karthik Iyer', status: 'Present', checkIn: '08:58 AM', checkOut: '—', hours: '—' },
]
