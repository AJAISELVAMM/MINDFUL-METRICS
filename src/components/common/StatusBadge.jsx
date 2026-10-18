const map = {
  Completed: 'bg-[#ECFDF5] text-[#10B981] border-[#D1FAE5]',
  Approved: 'bg-[#ECFDF5] text-[#10B981] border-[#D1FAE5]',
  Present: 'bg-[#ECFDF5] text-[#10B981] border-[#D1FAE5]',
  Active: 'bg-[#ECFDF5] text-[#10B981] border-[#D1FAE5]',
  Pending: 'bg-[#FFFBEB] text-[#F59E0B] border-[#FEF3C7]',
  'In Progress': 'bg-[#EFF6FF] text-[#1E6BFF] border-[#DBEAFE]',
  Working: 'bg-[#EFF6FF] text-[#1E6BFF] border-[#DBEAFE]',
  Late: 'bg-[#FFFBEB] text-[#F59E0B] border-[#FEF3C7]',
  Rejected: 'bg-[#FEF2F2] text-[#EF4444] border-[#FEE2E2]',
  Overdue: 'bg-[#FEF2F2] text-[#EF4444] border-[#FEE2E2]',
  Absent: 'bg-[#FEF2F2] text-[#EF4444] border-[#FEE2E2]',
  High: 'bg-[#FEF2F2] text-[#EF4444] border-[#FEE2E2]',
  Moderate: 'bg-[#FFFBEB] text-[#F59E0B] border-[#FEF3C7]',
  Low: 'bg-[#ECFDF5] text-[#10B981] border-[#D1FAE5]',
  Blocked: 'bg-[#FEF2F2] text-[#EF4444] border-[#FEE2E2]',
  'Not Started': 'bg-[#F1F5F9] text-[#64748B] border-[#E2E8F0]',
  'Half-Day': 'bg-amber-50 text-amber-700 border-amber-200',
  HALF_DAY: 'bg-amber-50 text-amber-700 border-amber-200',
  'Weekly Off': 'bg-purple-50 text-purple-700 border-purple-200',
  WEEKLY_OFF: 'bg-purple-50 text-purple-700 border-purple-200',
  Holiday: 'bg-indigo-50 text-indigo-700 border-indigo-200',
  HOLIDAY: 'bg-indigo-50 text-indigo-700 border-indigo-200',
  'On Leave': 'bg-blue-50 text-blue-700 border-blue-200',
  ON_LEAVE: 'bg-blue-50 text-blue-700 border-blue-200',
  LEAVE: 'bg-blue-50 text-blue-700 border-blue-200',
  Upcoming: 'bg-slate-50 text-slate-400 border-slate-200',
  FUTURE: 'bg-slate-50 text-slate-400 border-slate-200',
  Exception: 'bg-amber-50 text-amber-700 border-amber-200',
  ATTENDANCE_EXCEPTION: 'bg-amber-50 text-amber-700 border-amber-200',
  PRESENT: 'bg-[#ECFDF5] text-[#10B981] border-[#D1FAE5]',
  ABSENT: 'bg-[#FEF2F2] text-[#EF4444] border-[#FEE2E2]',
  LATE: 'bg-[#FFFBEB] text-[#F59E0B] border-[#FEF3C7]',
  'Almost Completed': 'bg-[#ECFDF5] text-[#059669] border-[#A7F3D0]',
  'Awaiting Verification': 'bg-[#FFFBEB] text-[#D97706] border-[#FDE68A]',
  'Verified': 'bg-[#ECFDF5] text-[#10B981] border-[#D1FAE5]',
  'Changes Requested': 'bg-[#FEF2F2] text-[#DC2626] border-[#FECACA]',
  'Pending HR Review': 'bg-[#FFFBEB] text-[#D97706] border-[#FDE68A]',
  'More Information Required': 'bg-[#EFF6FF] text-[#2563EB] border-[#BFDBFE]',
}

export default function StatusBadge({ status }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wider ${
        map[status] || 'bg-[#F1F5F9] text-[#64748B] border-[#E2E8F0]'
      }`}
    >
      {status}
    </span>
  )
}
