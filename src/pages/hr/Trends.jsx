import { useState, useEffect } from 'react'
import ChartCard from '../../components/common/ChartCard'
import { orgTrend } from '../../data/chartData'
import { getHRTrends } from '../../services/api'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, Legend } from 'recharts'

export default function OrgTrends() {
  const [f, setF] = useState('6 Months')
  const [liveData, setLiveData] = useState(null)

  useEffect(() => {
    getHRTrends()
      .then((res) => {
        if (res && res.trends) setLiveData(res.trends)
      })
      .catch(() => {})
  }, [])

  const count = f === '1 Month' ? 1 : f === '3 Months' ? 3 : f === '6 Months' ? 6 : 12
  const base = liveData && liveData.length > 0 ? liveData : orgTrend
  const sliceData = base.length >= count ? base.slice(-count) : base
  const trendData = sliceData.map((item, i) => ({
    ...item,
    month: item.month || `M${i + 1}`,
  }))
  return (
    <div className="page-stack fade-in">
      <div className="flex gap-2">{['1 Month', '3 Months', '6 Months', '1 Year'].map((x) => (
        <button key={x} type="button" onClick={() => setF(x)} className={`rounded-full px-3 py-1 text-xs ${f === x ? 'bg-blue-600 text-white' : 'border bg-white'}`}>{x}</button>
      ))}</div>
      <ChartCard title="Organization indicators">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={trendData}>
            <CartesianGrid stroke="#eef2f7" vertical={false} />
            <XAxis dataKey="month" tick={{ fontSize: 11 }} />
            <YAxis width={28} />
            <Tooltip />
            <Legend />
            <Line dataKey="burnout" stroke="#ef4444" dot={false} />
            <Line dataKey="stress" stroke="#f59e0b" dot={false} />
            <Line dataKey="workload" stroke="#3b82f6" dot={false} />
            <Line dataKey="overtime" stroke="#64748b" dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>
    </div>
  )
}
