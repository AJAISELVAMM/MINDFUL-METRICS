export default function RatingScale({ value, onChange, low, high }) {
  return (
    <div>
      <div className="flex gap-2">
        {[1, 2, 3, 4, 5].map((n) => (
          <button
            key={n}
            type="button"
            onClick={() => onChange(n)}
            className={`h-12 flex-1 rounded-xl border text-sm font-semibold transition duration-150 ${
              value === n
                ? 'border-[#1E6BFF] bg-[#1E6BFF] text-white shadow-[0_4px_14px_rgba(30,107,255,0.3)]'
                : 'border-[#E2EAF2] bg-white text-[#0D192B] hover:border-[#1E6BFF]/40 hover:bg-[#F8FAFC]'
            }`}
            aria-label={`Rate ${n}`}
          >
            {n}
          </button>
        ))}
      </div>
      <div className="mt-1.5 flex justify-between text-[11px] text-[#6B7C93]">
        <span>{low}</span>
        <span>{high}</span>
      </div>
    </div>
  )
}
