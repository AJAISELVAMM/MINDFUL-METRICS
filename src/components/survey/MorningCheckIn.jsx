import { useState, useEffect } from 'react'
import { morningWellbeing, morningWork } from '../../data/surveyData'
import { workPlanToday } from '../../data/workData'
import { getSurveyQuestions } from '../../services/api'
import RatingScale from './RatingScale'
import WorkPlanCard from './WorkPlanCard'

export default function MorningCheckIn({ onSubmit, submitting }) {
  const [step, setStep] = useState(1)
  const [answers, setAnswers] = useState({})
  const [wellbeingQs, setWellbeingQs] = useState(morningWellbeing)
  const [workQs, setWorkQs] = useState(morningWork)

  useEffect(() => {
    getSurveyQuestions()
      .then((data) => {
        if (data?.wellbeing && Array.isArray(data.wellbeing) && data.wellbeing.length > 0) {
          setWellbeingQs(data.wellbeing)
        }
        if (data?.work && Array.isArray(data.work) && data.work.length > 0) {
          setWorkQs(data.work)
        }
      })
      .catch(() => {})
  }, [])

  const qs = step === 1 ? wellbeingQs : workQs
  const ready = qs.every((q) => answers[q.id])

  return (
    <div className="card p-6 fade-in">
      <div className="mb-5 flex gap-2">
        {['01 Wellbeing', "02 Today's Work Plan"].map((s, i) => (
          <span key={s} className={`rounded-full px-3 py-1 text-[11px] font-semibold ${step === i + 1 ? 'bg-[#EFF6FF] text-[#1E6BFF]' : 'bg-[#F1F5F9] text-[#64748B]'}`}>{s}</span>
        ))}
      </div>
      <h2 className="text-[18px] font-bold text-[#0D192B]">Start-of-Day Check-in</h2>
      <p className="mb-5 text-[13px] text-[#6B7C93]">Capture how you feel now and what you expect from today&apos;s work.</p>
      {step === 2 && <div className="mb-5"><WorkPlanCard plan={workPlanToday} /></div>}
      <div className="space-y-6">
        {qs.map((q) => (
          <div key={q.id} className="rounded-xl border border-[#E3EBF3] p-4">
            <p className="mb-3 text-[13px] font-medium text-[#172B4D]">{q.label}</p>
            <RatingScale value={answers[q.id]} onChange={(n) => setAnswers({ ...answers, [q.id]: n })} low={q.low} high={q.high} />
          </div>
        ))}
      </div>
      <div className="mt-6 flex justify-between">
        {step === 2 ? (
          <button type="button" className="btn-secondary" onClick={() => setStep(1)}>Back</button>
        ) : <span />}
        {step === 1 ? (
          <button type="button" disabled={!ready} onClick={() => setStep(2)} className="btn-primary">Continue</button>
        ) : (
          <button type="button" disabled={!ready || submitting} onClick={() => onSubmit(answers)} className="btn-primary">{submitting ? 'Saving...' : 'Complete morning check-in'}</button>
        )}
      </div>
    </div>
  )
}
