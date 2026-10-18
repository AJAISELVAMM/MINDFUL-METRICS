import { Area, AreaChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

export default function StressTrendChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={data}>
        <CartesianGrid stroke="#E2EAF2" vertical={false} />
        <XAxis dataKey="day" tick={{ fontSize: 11, fill: '#64748B' }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fontSize: 11, fill: '#64748B' }} axisLine={false} tickLine={false} width={28} />
        <Tooltip contentStyle={{ borderRadius: 12, border: '1px solid #E2EAF2', fontSize: 12 }} />
        <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
        <Area type="monotone" dataKey="stress" stroke="#F59E0B" fill="#FFFBEB" name="Stress" />
        <Area type="monotone" dataKey="workload" stroke="#1E6BFF" fill="#EFF6FF" name="Workload" />
      </AreaChart>
    </ResponsiveContainer>
  )
}
