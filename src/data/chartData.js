export const burnoutTrend7 = [
  { day: 'Wed', value: 58 },
  { day: 'Thu', value: 61 },
  { day: 'Fri', value: 63 },
  { day: 'Sat', value: 55 },
  { day: 'Sun', value: 52 },
  { day: 'Mon', value: 68 },
  { day: 'Tue', value: 72 },
]

export const hoursWeek = [
  { day: 'Mon', hours: 9.2, ot: 1.2 },
  { day: 'Tue', hours: 8.6, ot: 0.6 },
  { day: 'Wed', hours: 9.8, ot: 1.8 },
  { day: 'Thu', hours: 8.4, ot: 0.4 },
  { day: 'Fri', hours: 9.1, ot: 1.1 },
  { day: 'Sat', hours: 0, ot: 0 },
  { day: 'Sun', hours: 0, ot: 0 },
]

export const stressTrend = [
  { day: 'Wed', stress: 52, workload: 55 },
  { day: 'Thu', stress: 54, workload: 58 },
  { day: 'Fri', stress: 61, workload: 62 },
  { day: 'Sat', stress: 40, workload: 20 },
  { day: 'Sun', stress: 38, workload: 18 },
  { day: 'Mon', stress: 64, workload: 66 },
  { day: 'Tue', stress: 68, workload: 61 },
]

export const expectedActualToday = [
  { metric: 'Workload', expected: 3, actual: 5 },
  { metric: 'Stress', expected: 2, actual: 4 },
  { metric: 'Difficulty', expected: 3, actual: 5 },
  { metric: 'Blockers', expected: 2, actual: 4 },
  { metric: 'Overtime likelihood', expected: 2, actual: 4 },
]

export const teamRiskDist = [
  { name: 'High', value: 4, fill: '#ef4444' },
  { name: 'Moderate', value: 8, fill: '#f59e0b' },
  { name: 'Low', value: 12, fill: '#22c55e' },
]

export const orgRiskDist = [
  { name: 'High', value: 18, fill: '#ef4444' },
  { name: 'Moderate', value: 46, fill: '#f59e0b' },
  { name: 'Low', value: 88, fill: '#22c55e' },
]

export const departmentBurnout = [
  { name: 'Engineering', risk: 71, workload: 78, stress: 69, overtime: 22 },
  { name: 'Testing', risk: 58, workload: 62, stress: 55, overtime: 14 },
  { name: 'Design', risk: 49, workload: 54, stress: 48, overtime: 8 },
  { name: 'Support', risk: 64, workload: 70, stress: 66, overtime: 18 },
  { name: 'HR', risk: 41, workload: 46, stress: 39, overtime: 6 },
  { name: 'Sales', risk: 56, workload: 61, stress: 58, overtime: 12 },
]

export const orgTrend = [
  { month: 'Apr', burnout: 48, stress: 51, workload: 54, overtime: 9, productivity: 72, sentiment: 68 },
  { month: 'May', burnout: 50, stress: 53, workload: 56, overtime: 10, productivity: 71, sentiment: 66 },
  { month: 'Jun', burnout: 52, stress: 55, workload: 58, overtime: 12, productivity: 70, sentiment: 64 },
  { month: 'Jul', burnout: 55, stress: 58, workload: 61, overtime: 14, productivity: 69, sentiment: 62 },
  { month: 'Aug', burnout: 58, stress: 60, workload: 64, overtime: 16, productivity: 68, sentiment: 60 },
  { month: 'Sep', burnout: 61, stress: 63, workload: 67, overtime: 18, productivity: 67, sentiment: 58 },
]

export const communicationSentiment = [
  { week: 'W1', positive: 62, neutral: 28, negative: 10 },
  { week: 'W2', positive: 58, neutral: 30, negative: 12 },
  { week: 'W3', positive: 54, neutral: 31, negative: 15 },
  { week: 'W4', positive: 51, neutral: 32, negative: 17 },
]
