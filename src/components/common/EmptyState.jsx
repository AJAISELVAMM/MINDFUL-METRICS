export default function EmptyState({ title, body }) {
  return (
    <div className="card flex flex-col items-center justify-center px-6 py-14 text-center">
      <p className="text-[14px] font-semibold text-[#172B4D]">{title}</p>
      {body && <p className="mt-1 text-[13px] text-[#6B7C93]">{body}</p>}
    </div>
  )
}
