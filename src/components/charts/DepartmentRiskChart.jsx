import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

export default function DepartmentRiskChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} layout="vertical" margin={{ left: 8 }} barSize={10}>
        <CartesianGrid stroke="#E2EAF2" horizontal={false} />
        <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11, fill: '#64748B' }} />
        <YAxis type="category" dataKey="name" width={90} tick={{ fontSize: 11, fill: '#64748B' }} />
        <Tooltip contentStyle={{ borderRadius: 12, border: '1px solid #E2EAF2', fontSize: 12 }} />
        <Bar dataKey="risk" fill="#1E6BFF" radius={[0, 6, 6, 0]} name="Burnout risk" />
      </BarChart>
    </ResponsiveContainer>
  )
}
