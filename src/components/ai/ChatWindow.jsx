import { Send, Sparkles } from 'lucide-react'
import { useState } from 'react'
import { sendAssistantMessage } from '../../services/api'

export default function ChatWindow({ role, suggestions, title, subtitle }) {
  const [msgs, setMsgs] = useState([
    { from: 'ai', text: 'I can help you interpret work-pattern and wellbeing indicators. Ask a question or pick a suggestion.', time: 'Now' },
  ])
  const [input, setInput] = useState('')
  const [typing, setTyping] = useState(false)

  async function send(text) {
    const t = text.trim()
    if (!t) return
    const currentMsgs = msgs
    setMsgs((m) => [...m, { from: 'user', text: t, time: 'Now' }])
    setInput('')
    setTyping(true)
    try {
      const history = currentMsgs.slice(-6).map((m) => ({ from: m.from, text: m.text }))
      let lastPage = `${role}_dashboard`
      try {
        lastPage = sessionStorage.getItem('mm_last_page') || lastPage
      } catch {}
      const pageContext = { page: lastPage, current_route: window.location.pathname }
      const reply = await sendAssistantMessage(role, t, {
        page_context: pageContext,
        conversation_history: history,
      })
      setMsgs((m) => [...m, { from: 'ai', text: reply, time: 'Now' }])
    } catch {
      setMsgs((m) => [...m, { from: 'ai', text: 'The assistant is unavailable right now. Please try again.', time: 'Now' }])
    } finally {
      setTyping(false)
    }
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_280px]">
      <div className="card flex h-[640px] flex-col overflow-hidden">
        <div className="border-b border-[#E2EAF2] px-5 py-4">
          <div className="flex items-center gap-2">
            <Sparkles size={16} className="text-[#1E6BFF]" />
            <h2 className="text-[14px] font-bold text-[#0D192B]">{title}</h2>
          </div>
          <p className="mt-0.5 text-[12px] text-[#64748B]">{subtitle}</p>
        </div>
        <div className="flex-1 space-y-3 overflow-y-auto p-4">
          {msgs.map((m, i) => (
            <div key={i} className={`flex ${m.from === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] rounded-2xl px-3.5 py-2.5 text-[13px] leading-relaxed ${m.from === 'user' ? 'bg-[#1E6BFF] text-white shadow-sm' : 'bg-[#F1F5F9] text-[#0D192B]'}`}>
                {m.text}
                <p className={`mt-1 text-[10px] ${m.from === 'user' ? 'text-blue-100' : 'text-[#94A3B8]'}`}>{m.time}</p>
              </div>
            </div>
          ))}
          {typing && (
            <div className="flex gap-1 px-2">
              {[0, 1, 2].map((i) => (
                <span key={i} className="h-1.5 w-1.5 rounded-full bg-[#94A3B8]" style={{ animation: 'pulseDot 1s infinite', animationDelay: `${i * 0.15}s` }} />
              ))}
            </div>
          )}
        </div>
        <form
          className="flex gap-2 border-t border-[#E2EAF2] p-3"
          onSubmit={(e) => {
            e.preventDefault()
            send(input)
          }}
        >
          <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask about work patterns…" className="ww-input mt-0" />
          <button type="submit" className="btn-primary px-4 rounded-xl" aria-label="Send"><Send size={16} /></button>
        </form>
      </div>
      <div className="hidden space-y-3 lg:block">
        <p className="text-[12px] font-bold uppercase tracking-wider text-[#64748B]">Suggested</p>
        {suggestions.map((s) => (
          <button key={s} type="button" onClick={() => send(s)} className="card w-full p-3 text-left text-[13px] font-medium text-[#0D192B] hover:border-[#1E6BFF]/40 hover:bg-[#F8FAFC]">
            {s}
          </button>
        ))}
      </div>
    </div>
  )
}
