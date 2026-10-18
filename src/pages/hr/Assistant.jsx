import ChatWindow from '../../components/ai/ChatWindow'

export default function HRAssistant() {
  return (
    <ChatWindow
      role="hr"
      title="AI HR Assistant"
      subtitle="Organization-level wellbeing analytics."
      suggestions={[
        'Which department has the highest burnout risk?',
        'What are the major risk indicators this month?',
        'Summarize organization wellbeing this week.',
        'Which departments show increasing risk?',
        'Compare workload trends across departments.',
      ]}
    />
  )
}
