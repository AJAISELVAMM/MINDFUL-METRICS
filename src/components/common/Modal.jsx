import { useEffect } from 'react'

export default function Modal({ open, title, children, onClose, footer, maxWidth = 'max-w-lg' }) {
  useEffect(() => {
    if (!open) return
    const originalStyle = window.getComputedStyle(document.body).overflow
    document.body.style.overflow = 'hidden'

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose?.()
      }
    }
    window.addEventListener('keydown', handleKeyDown)

    return () => {
      document.body.style.overflow = originalStyle
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [open, onClose])

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 md:p-6 overflow-hidden"
      role="dialog"
      aria-modal="true"
    >
      <button
        type="button"
        className="absolute inset-0 bg-[#0F2035]/40 backdrop-blur-[3px] transition-opacity"
        aria-label="Close"
        onClick={onClose}
      />
      <div
        className={`card relative z-10 w-full ${maxWidth} max-h-[calc(100dvh-1.5rem)] sm:max-h-[calc(100dvh-3rem)] flex flex-col p-0 overflow-hidden shadow-2xl fade-in`}
      >
        <div className="shrink-0 flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-white">
          <h2 className="text-[16px] font-semibold text-[#172B4D] truncate pr-2">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-[#6B7C93] hover:bg-[#EEF5FA] transition-colors"
            aria-label="Close dialog"
          >
            ✕
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-4 min-h-0 overscroll-contain">
          {children}
        </div>

        {footer && (
          <div className="shrink-0 px-6 py-3.5 border-t border-slate-100 bg-slate-50/70 rounded-b-2xl">
            {footer}
          </div>
        )}
      </div>
    </div>
  )
}

