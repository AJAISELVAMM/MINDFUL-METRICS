import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

export default function WorkloadChart({ data }) {
  // Ensure we have standard week day mapping if data is 5 days or 7 days
  const chartData = data?.length
    ? data
    : [
        { day: 'Mon', hours: 7.5 },
        { day: 'Tue', hours: 6.8 },
        { day: 'Wed', hours: 9.2 },
        { day: 'Thu', hours: 8.5 },
        { day: 'Fri', hours: 5.6 },
        { day: 'Sat', hours: 4.0 },
        { day: 'Sun', hours: 6.2 },
      ]

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart
        data={chartData}
        barSize={14}
        margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
      >
        <CartesianGrid stroke="#EDF2F7" vertical={false} strokeDasharray="3 3" />
        <XAxis
          dataKey="day"
          tick={{ fontSize: 11, fill: '#94A3B8', fontWeight: 500 }}
          axisLine={false}
          tickLine={false}
          dy={8}
        />
        <YAxis
          domain={[0, 12]}
          ticks={[0, 4, 8, 12]}
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
          formatter={(val) => [`${val} hrs`, 'Working Hours']}
        />
        <Bar
          dataKey="hours"
          fill="#1E6BFF"
          radius={[5, 5, 0, 0]}
          name="Hours"
        />
      </BarChart>
    </ResponsiveContainer>
  )
}
