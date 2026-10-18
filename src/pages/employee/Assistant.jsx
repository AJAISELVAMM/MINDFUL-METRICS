import ChatWindow from '../../components/ai/ChatWindow'

export default function Assistant() {
  return (
    <ChatWindow
      role="employee"
      title="AI Wellness Assistant"
      subtitle="Understand your work and wellbeing patterns."
      suggestions={[
        'Why is my burnout risk high?',
        'How was my week?',
        'What changed from last week?',
        'How is my workload?',
        'Compare my expected and actual workload.',
      ]}
    />
  )
}
