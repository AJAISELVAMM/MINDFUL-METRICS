import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

export default function ComparisonChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} barSize={12}>
        <CartesianGrid stroke="#E2EAF2" vertical={false} />
        <XAxis dataKey="metric" tick={{ fontSize: 10, fill: '#64748B' }} axisLine={false} tickLine={false} />
        <YAxis domain={[0, 5]} tick={{ fontSize: 11, fill: '#64748B' }} axisLine={false} tickLine={false} width={24} />
        <Tooltip contentStyle={{ borderRadius: 12, border: '1px solid #E2EAF2', fontSize: 12 }} />
        <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
        <Bar dataKey="expected" fill="#93C5FD" radius={[4, 4, 0, 0]} name="Expected" />
        <Bar dataKey="actual" fill="#1E6BFF" radius={[4, 4, 0, 0]} name="Actual" />
      </BarChart>
    </ResponsiveContainer>
  )
}
