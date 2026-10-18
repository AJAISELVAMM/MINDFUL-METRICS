import { useEffect } from 'react'

export default function Drawer({ open, title, children, onClose, width = 'max-w-md' }) {
  useEffect(() => {
    if (!open) return
    const originalStyle = window.getComputedStyle(document.body).overflow
    document.body.style.overflow = 'hidden'

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose?.()
    }
    window.addEventListener('keydown', handleKeyDown)

    return () => {
      document.body.style.overflow = originalStyle
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 overflow-hidden" role="dialog" aria-modal="true">
      <button
        type="button"
        className="absolute inset-0 bg-[#0F2035]/40 backdrop-blur-[3px] transition-opacity"
        aria-label="Close drawer"
        onClick={onClose}
      />
      <aside className={`absolute right-0 top-0 h-full w-full ${width} max-w-full overflow-y-auto rounded-l-2xl bg-white p-6 shadow-2xl fade-in overscroll-contain`}>
        <div className="sticky top-0 z-20 -mx-6 -mt-6 mb-5 flex items-center justify-between bg-white px-6 py-4 border-b border-slate-100">
          <h2 className="text-[16px] font-semibold text-[#172B4D] truncate pr-2">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-[#6B7C93] hover:bg-[#EEF5FA] transition-colors"
            aria-label="Close"
          >
            ✕
          </button>
        </div>
        {children}
      </aside>
    </div>
  )
}

