import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

export default function BurnoutTrendChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
        <defs>
          <linearGradient id="burnoutGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#1E6BFF" stopOpacity={0.28} />
            <stop offset="60%" stopColor="#1E6BFF" stopOpacity={0.08} />
            <stop offset="100%" stopColor="#1E6BFF" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke="#EDF2F7" vertical={false} strokeDasharray="3 3" />
        <XAxis
          dataKey="day"
          tick={{ fontSize: 11, fill: '#94A3B8', fontWeight: 500 }}
          axisLine={false}
          tickLine={false}
          dy={8}
        />
        <YAxis
          domain={[0, 100]}
          ticks={[0, 50, 100]}
          tick={{ fontSize: 11, fill: '#94A3B8', fontWeight: 500 }}
          axisLine={false}
          tickLine={false}
          width={36}
        />
        <Tooltip
          contentStyle={{
            borderRadius: 12,
            border: '1px solid #E2EAF2',
            boxShadow: '0 8px 24px rgba(15,30,60,0.08)',
            fontSize: 12,
            fontWeight: 500,
          }}
          formatter={(val) => [`${val} / 100`, 'Burnout Risk']}
        />
        <Area
          type="monotone"
          dataKey="value"
          stroke="#1E6BFF"
          strokeWidth={2.5}
          fill="url(#burnoutGradient)"
          dot={{ r: 3, fill: '#1E6BFF', stroke: '#fff', strokeWidth: 2 }}
          activeDot={{ r: 5, fill: '#1E6BFF', stroke: '#fff', strokeWidth: 2.5 }}
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}
