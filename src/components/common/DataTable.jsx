export default function DataTable({ columns, rows, onRowClick }) {
  if (!rows?.length) {
    return (
      <div className="py-12 text-center text-[13px] text-[#94A3B8]">
        No records found.
      </div>
    )
  }

  return (
    <div className="overflow-x-auto rounded-2xl border border-[#E2EAF2]">
      <table className="w-full min-w-[640px] text-left text-[13px]">
        <thead>
          <tr className="bg-[#F8FAFC] border-b border-[#E2EAF2] text-[11px] font-bold uppercase tracking-wider text-[#64748B]">
            {columns.map((c) => (
              <th key={c.key} className="px-4 py-3.5">
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-[#E2EAF2] bg-white">
          {rows.map((row, i) => (
            <tr
              key={row.id || i}
              onClick={() => onRowClick?.(row)}
              className={`transition-colors hover:bg-[#F8FAFC] ${
                onRowClick ? 'cursor-pointer' : ''
              }`}
            >
              {columns.map((c) => (
                <td key={c.key} className="px-4 py-3.5 text-[#0D192B]">
                  {c.render ? c.render(row) : row[c.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
