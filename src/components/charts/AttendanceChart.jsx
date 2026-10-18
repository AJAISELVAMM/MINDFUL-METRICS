import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

export default function AttendanceChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} barSize={12}>
        <CartesianGrid stroke="#E2EAF2" vertical={false} />
        <XAxis dataKey="day" tick={{ fontSize: 11, fill: '#64748B' }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fontSize: 11, fill: '#64748B' }} axisLine={false} tickLine={false} width={28} />
        <Tooltip contentStyle={{ borderRadius: 12, border: '1px solid #E2EAF2', fontSize: 12 }} />
        <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
        <Bar dataKey="hours" fill="#1E6BFF" radius={[5, 5, 0, 0]} name="Hours" />
        <Bar dataKey="ot" fill="#F59E0B" radius={[5, 5, 0, 0]} name="Overtime" />
      </BarChart>
    </ResponsiveContainer>
  )
}
