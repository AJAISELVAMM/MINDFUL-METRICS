import { Bell, CheckCheck } from 'lucide-react'
import { useEffect, useState, useRef, useCallback } from 'react'
import {
  getNotifications,
  markNotificationRead,
  markAllNotificationsRead,
} from '../../services/api'

export default function NotificationDropdown() {
  const [open, setOpen] = useState(false)
  const [items, setItems] = useState([])
  const [error, setError] = useState(false)
  const [markingAll, setMarkingAll] = useState(false)
  const dropdownRef = useRef(null)
  const pendingReadsRef = useRef(new Set())

  const loadNotifs = useCallback(() => {
    getNotifications()
      .then((data) => {
        setItems(Array.isArray(data) ? data : [])
        setError(false)
      })
      .catch(() => setError(true))
  }, [])

  // Initial load & visibility-aware lightweight polling (Phase 11)
  useEffect(() => {
    loadNotifs()

    const interval = setInterval(() => {
      if (document.visibilityState === 'visible') {
        loadNotifs()
      }
    }, 30000)

    const handleRefresh = () => {
      loadNotifs()
    }

    const handleVisibility = () => {
      if (document.visibilityState === 'visible') {
        loadNotifs()
      }
    }

    window.addEventListener('mindful-metrics-refresh', handleRefresh)
    document.addEventListener('visibilitychange', handleVisibility)

    return () => {
      clearInterval(interval)
      window.removeEventListener('mindful-metrics-refresh', handleRefresh)
      document.removeEventListener('visibilitychange', handleVisibility)
    }
  }, [loadNotifs])

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(e) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setOpen(false)
      }
    }
    if (open) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [open])

  const unreadCount = items.filter((n) => n.unread).length

  async function handleNotificationClick(e, n) {
    if (e) {
      e.preventDefault()
      e.stopPropagation()
    }

    if (!n || !n.id) return

    // If it was already read, do not call API or decrease count again
    if (!n.unread && n.is_read) {
      return
    }

    // Prevent duplicate API requests caused by repeated clicks
    if (pendingReadsRef.current.has(n.id)) {
      return
    }
    pendingReadsRef.current.add(n.id)

    try {
      const res = await markNotificationRead(n.id)
      if (res && res.ok !== false) {
        // Update read state in frontend immediately after successful response
        setItems((prev) =>
          prev.map((item) =>
            item.id === n.id ? { ...item, unread: false, is_read: true } : item
          )
        )
      }
    } catch (err) {
      // Retain unread state on failure; do not claim it is read
      console.error('Failed to mark notification as read:', err)
    } finally {
      pendingReadsRef.current.delete(n.id)
    }
  }

  async function handleMarkAllRead(e) {
    e.stopPropagation()
    if (unreadCount === 0 || markingAll) return
    setMarkingAll(true)

    // Optimistic update
    setItems((prev) =>
      prev.map((item) => ({ ...item, unread: false, is_read: true }))
    )

    try {
      await markAllNotificationsRead()
    } catch {
      loadNotifs()
    } finally {
      setMarkingAll(false)
    }
  }

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        type="button"
        aria-label="Notifications"
        onClick={() => setOpen((v) => !v)}
        className="relative flex h-9 w-9 items-center justify-center rounded-xl border border-[#E2EAF2] bg-white text-[#64748B] transition hover:border-[#1E6BFF]/40 hover:text-[#1E6BFF] shadow-sm"
      >
        <Bell size={17} />
        {unreadCount > 0 && (
          <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-[#EF4444] ring-2 ring-white" />
        )}
      </button>

      {open && (
        <div className="absolute right-0 z-30 mt-2 w-[min(22rem,calc(100vw-2rem))] overflow-hidden rounded-2xl border border-[#E2EAF2] bg-white p-2 shadow-[0_12px_36px_rgba(15,30,60,0.12)]">
          <div className="flex items-center justify-between px-3 py-2 border-b border-[#E2EAF2]/60">
            <div className="flex items-center gap-2">
              <p className="text-[12px] font-bold uppercase tracking-wider text-[#64748B]">Notifications</p>
              {unreadCount > 0 && (
                <span className="rounded-full bg-[#FEF2F2] text-[#EF4444] text-[10px] font-bold px-2 py-0.5">
                  {unreadCount} new
                </span>
              )}
            </div>

            {unreadCount > 0 && (
              <button
                type="button"
                onClick={handleMarkAllRead}
                disabled={markingAll}
                className="inline-flex items-center gap-1 text-[11px] font-medium text-[#1E6BFF] hover:underline"
              >
                <CheckCheck size={13} />
                Mark all read
              </button>
            )}
          </div>

          {error && (
            <p className="px-3 py-3 text-[12px] text-[#94A3B8]">
              Notifications are unavailable right now.
            </p>
          )}

          <div className="max-h-80 overflow-y-auto divide-y divide-[#E2EAF2]/50">
            {items.map((n) => {
              const isUnread = Boolean(n.unread)
              return (
                <div
                  key={n.id}
                  onClick={(e) => handleNotificationClick(e, n)}
                  className={`p-3 transition rounded-xl cursor-pointer ${
                    isUnread
                      ? 'bg-[#F4F8FF]/80 hover:bg-[#EBF2FF]'
                      : 'hover:bg-[#F8FAFC]'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <p
                      className={`text-[13px] ${
                        isUnread
                          ? 'font-bold text-[#0D192B]'
                          : 'font-semibold text-[#334155]'
                      }`}
                    >
                      {n.title}
                    </p>
                    {isUnread && (
                      <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-[#1E6BFF]" />
                    )}
                  </div>

                  <p className="text-[12px] text-[#64748B] mt-0.5 leading-snug">
                    {n.body}
                  </p>

                  <div className="mt-1.5 flex items-center justify-between text-[10px] text-[#94A3B8]">
                    <span>{n.time}</span>
                    {n.priority === 'critical' && (
                      <span className="text-red-600 font-semibold uppercase text-[9px]">Critical</span>
                    )}
                    {n.priority === 'high' && (
                      <span className="text-amber-600 font-semibold uppercase text-[9px]">Important</span>
                    )}
                  </div>
                </div>
              )
            })}

            {items.length === 0 && !error && (
              <p className="py-6 text-center text-xs text-[#94A3B8]">No notifications</p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
