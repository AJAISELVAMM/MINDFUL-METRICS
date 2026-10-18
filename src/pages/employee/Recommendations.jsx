import { useEffect, useState } from 'react'
import { Briefcase, Heart, Clock, Scale, MessageSquare } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import RecommendationCard from '../../components/ai/RecommendationCard'
import { getRecommendations } from '../../services/api'
import LoadingSkeleton from '../../components/common/LoadingSkeleton'

const iconMap = {
  Workload: { icon: Briefcase, path: '/employee/work' },
  Wellbeing: { icon: Heart, path: '/employee/attendance' },
  'Time Management': { icon: Clock, path: '/employee/attendance' },
  'Work-Life Balance': { icon: Scale, path: '/employee/burnout' },
  Communication: { icon: MessageSquare, path: '/employee/assistant' },
}

export default function Recommendations() {
  const nav = useNavigate()
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getRecommendations()
      .then((data) => {
        const raw = data?.items || []
        const formatted = raw.map((item) => {
          const matched = iconMap[item.category] || { icon: Heart, path: '/employee/dashboard' }
          return {
            category: item.category,
            body: item.body,
            icon: matched.icon,
            path: matched.path,
          }
        })
        setItems(formatted)
      })
      .catch(() => setItems([]))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <LoadingSkeleton rows={2} />

  return (
    <div className="page-stack fade-in">
      <p className="text-[13px] text-[#6B7C93]">
        Supportive workplace work-pattern recommendations based on recent workload and attendance signals. Not medical advice or diagnosis.
      </p>
      <div className="grid gap-4 md:grid-cols-2">
        {items.map((r, i) => (
          <RecommendationCard key={i} {...r} onAction={() => nav(r.path)} />
        ))}
      </div>
    </div>
  )
}
