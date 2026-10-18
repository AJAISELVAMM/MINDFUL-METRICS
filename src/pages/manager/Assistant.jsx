import ChatWindow from '../../components/ai/ChatWindow'

export default function ManagerAssistant() {
  return (
    <ChatWindow
      role="manager"
      title="AI Team Assistant"
      subtitle="Team-level wellbeing and workload insights."
      suggestions={[
        'Which team member has the highest risk?',
        'Why did team burnout increase?',
        "Summarize this week's team wellbeing.",
        'Which workload patterns need attention?',
        'Which team members show increasing stress?',
      ]}
    />
  )
}
