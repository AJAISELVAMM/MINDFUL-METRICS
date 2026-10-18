export const leaveBalance = [
  { type: 'Casual Leave', remaining: 4, total: 12, color: '#3b82f6' },
  { type: 'Sick Leave', remaining: 3, total: 8, color: '#f59e0b' },
  { type: 'Earned Leave', remaining: 8, total: 15, color: '#22c55e' },
]

export const leaveHistory = [
  { id: 'L-2041', date: '18 Sep 2026', type: 'Casual Leave', duration: '1 day', reason: 'Family function', status: 'Approved' },
  { id: 'L-2018', date: '02 Sep 2026', type: 'Sick Leave', duration: '1 day', reason: 'Fever', status: 'Approved' },
  { id: 'L-1992', date: '14 Aug 2026', type: 'Earned Leave', duration: '2 days', reason: 'Travel', status: 'Approved' },
  { id: 'L-1970', date: '28 Jul 2026', type: 'Casual Leave', duration: '1 day', reason: 'Personal errand', status: 'Rejected' },
  { id: 'L-2055', date: '22 Sep 2026', type: 'Casual Leave', duration: '1 day', reason: 'Appointment', status: 'Pending' },
]

export const teamLeaveRequests = [
  { id: 'LR-881', employee: 'Rahul Sharma', empId: 'E102', type: 'Casual Leave', date: '12 Sep 2026', duration: '1 day', reason: 'Personal work', status: 'Pending' },
  { id: 'LR-882', employee: 'Anita Krishnan', empId: 'E109', type: 'Sick Leave', date: '11 Sep 2026', duration: '2 days', reason: 'Medical rest', status: 'Pending' },
  { id: 'LR-870', employee: 'Vikram Rao', empId: 'E121', type: 'Earned Leave', date: '05 Sep 2026', duration: '3 days', reason: 'Family travel', status: 'Approved' },
  { id: 'LR-861', employee: 'Sneha Reddy', empId: 'E130', type: 'Casual Leave', date: '01 Sep 2026', duration: '1 day', reason: 'Bank work', status: 'Rejected' },
]
