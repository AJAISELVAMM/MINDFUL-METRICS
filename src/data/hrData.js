export const hrProfile = {
  name: 'HR Team',
  firstName: 'HR Team',
  email: 'hr@mindfulmetrics.com',
  role: 'People Operations',
  department: 'HR',
}

export const employeesDirectory = [
  { id: 'E102', name: 'Rahul Sharma', dept: 'Engineering', role: 'Senior Engineer', status: 'Active', burnout: 86, workload: 88, lastCheckIn: '09:04 AM' },
  { id: 'E109', name: 'Anita Krishnan', dept: 'Engineering', role: 'Engineer', status: 'Active', burnout: 78, workload: 80, lastCheckIn: '09:18 AM' },
  { id: 'E118', name: 'Arjun Mehta', dept: 'Engineering', role: 'Software Engineer', status: 'Active', burnout: 72, workload: 61, lastCheckIn: '09:12 AM' },
  { id: 'E121', name: 'Vikram Rao', dept: 'Engineering', role: 'Engineer', status: 'Active', burnout: 66, workload: 70, lastCheckIn: '09:46 AM' },
  { id: 'E130', name: 'Sneha Reddy', dept: 'Testing', role: 'QA Engineer', status: 'On Leave', burnout: 62, workload: 68, lastCheckIn: '—' },
  { id: 'E141', name: 'Karthik Iyer', dept: 'Engineering', role: 'Frontend Engineer', status: 'Active', burnout: 44, workload: 55, lastCheckIn: '08:58 AM' },
  { id: 'E162', name: 'Divya Menon', dept: 'Design', role: 'Product Designer', status: 'Active', burnout: 47, workload: 52, lastCheckIn: '09:22 AM' },
  { id: 'E171', name: 'Imran Khan', dept: 'Support', role: 'Support Lead', status: 'Active', burnout: 64, workload: 70, lastCheckIn: '08:51 AM' },
  { id: 'E180', name: 'Lakshmi N', dept: 'Sales', role: 'Account Executive', status: 'Active', burnout: 56, workload: 61, lastCheckIn: '09:30 AM' },
  { id: 'E188', name: 'Nisha Patel', dept: 'HR', role: 'HR Business Partner', status: 'Active', burnout: 38, workload: 44, lastCheckIn: '09:05 AM' },
]

export const interventions = [
  {
    id: 'INT-12',
    employee: 'Rahul Sharma',
    empId: 'E102',
    initial: 82,
    current: 61,
    actions: ['Workload reviewed', 'Tasks redistributed', 'Follow-up planned'],
    timeline: [
      { date: '12 Aug', event: 'Risk flagged at 82' },
      { date: '14 Aug', event: 'Workload reviewed with manager' },
      { date: '21 Aug', event: 'Two high-priority tasks redistributed' },
      { date: '04 Sep', event: 'Follow-up check-in scheduled' },
      { date: '08 Sep', event: 'Risk indicators at 61' },
    ],
  },
  {
    id: 'INT-09',
    employee: 'Anita Krishnan',
    empId: 'E109',
    initial: 79,
    current: 78,
    actions: ['Manager 1:1 scheduled', 'Overtime monitored'],
    timeline: [
      { date: '28 Aug', event: 'Risk flagged at 79' },
      { date: '01 Sep', event: 'Manager 1:1 completed' },
      { date: '08 Sep', event: 'Risk indicators remain elevated at 78' },
    ],
  },
]

export const modelPerformance = {
  disclaimer: 'Demo / mock evaluation metrics for UI illustration only. Not a live trained model.',
  models: [
    { name: 'Random Forest', accuracy: 0.86, precision: 0.84, recall: 0.81, f1: 0.82 },
    { name: 'Logistic Regression', accuracy: 0.79, precision: 0.76, recall: 0.74, f1: 0.75 },
    { name: 'XGBoost', accuracy: 0.88, precision: 0.85, recall: 0.83, f1: 0.84 },
  ],
  features: [
    { name: 'Overtime hours', importance: 0.22 },
    { name: 'Workload score', importance: 0.18 },
    { name: 'Stress (evening)', importance: 0.16 },
    { name: 'Expected vs actual gap', importance: 0.14 },
    { name: 'Leave pattern', importance: 0.11 },
    { name: 'Communication sentiment', importance: 0.1 },
    { name: 'Work-life balance', importance: 0.09 },
  ],
  confusion: [
    [42, 6],
    [8, 44],
  ],
}
