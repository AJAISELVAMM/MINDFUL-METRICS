export default function LoadingSkeleton({ rows = 4 }) {
  return (
    <div className="page-stack fade-in">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="card h-24 animate-pulse bg-[#EAF3FF]" />
        ))}
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="card h-56 animate-pulse bg-[#EAF3FF]" />
        ))}
      </div>
    </div>
  )
}
