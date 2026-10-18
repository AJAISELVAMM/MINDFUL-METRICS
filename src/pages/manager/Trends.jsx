import { useState, useEffect } from 'react'
import ChartCard from '../../components/common/ChartCard'
import BurnoutTrendChart from '../../components/charts/BurnoutTrendChart'
import StressTrendChart from '../../components/charts/StressTrendChart'
import AttendanceChart from '../../components/charts/AttendanceChart'
import { burnoutTrend7, stressTrend, hoursWeek } from '../../data/chartData'
import { getManagerTrends } from '../../services/api'

export default function ManagerTrends() {
  const [f, setF] = useState('7 Days')
  const [liveData, setLiveData] = useState(null)

  useEffect(() => {
    getManagerTrends()
      .then((res) => {
        if (res && res.burnout_trend) setLiveData(res)
      })
      .catch(() => {})
  }, [])

  const count = f === '7 Days' ? 7 : f === '30 Days' ? 30 : 90
  const bData = liveData?.burnout_trend || burnoutTrend7
  const sData = liveData?.stress_trend || stressTrend
  const hData = liveData?.hours_trend || hoursWeek
  const oData = liveData?.overtime_trend || hoursWeek

  const expand = (data) => Array.from({ length: count }, (_, i) => ({ ...data[i % data.length], day: `${i + 1}` }))
  return (
    <div className="page-stack fade-in">
      <div className="flex gap-2">{['7 Days', '30 Days', '3 Months'].map((x) => (
        <button key={x} type="button" onClick={() => setF(x)} className={`rounded-full px-3 py-1 text-xs ${f === x ? 'bg-blue-600 text-white' : 'border bg-white'}`}>{x}</button>
      ))}</div>
      <div className="grid gap-3 lg:grid-cols-2">
        <ChartCard title="Burnout"><BurnoutTrendChart data={expand(bData)} /></ChartCard>
        <ChartCard title="Stress"><StressTrendChart data={expand(sData)} /></ChartCard>
        <ChartCard title="Attendance & Hours"><AttendanceChart data={expand(hData)} /></ChartCard>
        <ChartCard title="Overtime"><AttendanceChart data={expand(oData)} /></ChartCard>
      </div>
    </div>
  )
}
