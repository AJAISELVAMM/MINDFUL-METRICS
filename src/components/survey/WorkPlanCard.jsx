export default function WorkPlanCard({ plan }) {
  const items = [
    ['Tasks Assigned', plan.tasksAssigned],
    ['High Priority', plan.highPriority],
    ['Deadline Today', plan.deadlineToday],
    ['Estimated Workload', `${plan.estimatedHours} hrs`],
  ]
  return (
    <div className="rounded-2xl border border-[#E3EBF3] bg-[#F7FBFF] p-4">
      <p className="mb-3 text-[13px] font-semibold text-[#172B4D]">Today&apos;s Work Plan</p>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {items.map(([k, v]) => (
          <div key={k} className="rounded-xl bg-white p-3">
            <p className="text-[11px] text-[#6B7C93]">{k}</p>
            <p className="mt-1 text-[18px] font-semibold text-[#172B4D]">{v}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
