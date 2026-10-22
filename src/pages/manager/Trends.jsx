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

  const count = f === '7 Days' ? 7 : f === '30 Days' ? 30 : 90

  useEffect(() => {
    getManagerTrends(count)
      .then((res) => {
        if (res && res.burnout_trend) setLiveData(res)
      })
      .catch(() => {})
  }, [count])

  const bData = liveData?.burnout_trend || burnoutTrend7
  const sData = liveData?.stress_trend || stressTrend
  const hData = liveData?.hours_trend || hoursWeek
  const oData = liveData?.overtime_trend || hoursWeek

  return (
    <div className="page-stack fade-in">
      <div className="flex gap-2">{['7 Days', '30 Days', '3 Months'].map((x) => (
        <button key={x} type="button" onClick={() => setF(x)} className={`rounded-full px-3 py-1 text-xs ${f === x ? 'bg-blue-600 text-white' : 'border bg-white'}`}>{x}</button>
      ))}</div>
      <div className="grid gap-3 lg:grid-cols-2">
        <ChartCard title="Burnout"><BurnoutTrendChart data={bData} /></ChartCard>
        <ChartCard title="Stress"><StressTrendChart data={sData} /></ChartCard>
        <ChartCard title="Attendance & Hours"><AttendanceChart data={hData} showOt={false} /></ChartCard>
        <ChartCard title="Overtime"><AttendanceChart data={oData} showHours={false} /></ChartCard>
      </div>
    </div>
  )
}
