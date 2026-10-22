import { useState, useEffect, useRef } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { Mail, Lock, Eye, EyeOff } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import { wakeBackend, ensureBackendReady, isBackendWarm } from '../services/api'

export default function Login() {
  const { user, login } = useAuth()
  const nav = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [remember, setRemember] = useState(true)
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [isWaking, setIsWaking] = useState(false)
  const isSubmittingRef = useRef(false)

  // Wake backend proactively as soon as login page loads
  useEffect(() => {
    wakeBackend()
  }, [])

  if (user) {
    const r = (user.role || '').trim().toLowerCase()
    const path =
      r === 'manager'
        ? '/manager/dashboard'
        : r === 'hr'
        ? '/hr/dashboard'
        : '/employee/dashboard'
    return <Navigate to={path} replace />
  }

  async function submit(e) {
    e.preventDefault()
    if (loading || isSubmittingRef.current) {
      return
    }
    isSubmittingRef.current = true
    setError('')
    setLoading(true)

    try {
      // 1. If backend isn't verified warm yet, wait for health check with bounded retries
      if (!isBackendWarm()) {
        setIsWaking(true)
        const ready = await ensureBackendReady()
        if (!ready.ok) {
          setError(
            ready.error ||
              'The server is taking longer than expected to wake up. Please try again in a moment.'
          )
          return
        }
      }

      // 2. Submit the login request exactly once with user credentials
      setIsWaking(false)
      const res = await login(email, password, remember)
      if (!res.ok) {
        setError(res.error || 'Invalid credentials')
        return
      }

      // 3. Navigate to dashboard based on role
      const r = (res.session?.role || res.user?.role || '').trim().toLowerCase()
      nav(
        r === 'manager'
          ? '/manager/dashboard'
          : r === 'hr'
          ? '/hr/dashboard'
          : '/employee/dashboard'
      )
    } catch (err) {
      setError(err?.message || 'Login failed')
    } finally {
      setLoading(false)
      setIsWaking(false)
      isSubmittingRef.current = false
    }
  }

  return (
    <div
      className="relative min-h-screen w-full flex items-center justify-center p-4 sm:p-6 md:p-10 overflow-hidden bg-cover bg-center bg-no-repeat"
      style={{ backgroundImage: "url('/login-bg.jpg')" }}
    >
      {/* ===============================================================
          SUBTLE ANIMATED OVERLAYS (All pointer-events: none)
          =============================================================== */}

      {/* 1. Gentle Ambient Light Drift over the Scene */}
      <div
        className="pointer-events-none absolute -top-1/4 -left-1/4 w-[150%] h-[150%] animate-ambient-drift mix-blend-soft-light"
        style={{
          background:
            'radial-gradient(ellipse at 25% 25%, rgba(255, 255, 255, 0.45) 0%, rgba(224, 242, 254, 0.2) 35%, transparent 68%)',
        }}
      />

      {/* 2. Subtle Blue / Cyan Glow Pulse over Lower Floor Wave */}
      <div
        className="pointer-events-none absolute inset-x-0 bottom-0 h-[48%] animate-wave-glow"
        style={{
          background:
            'radial-gradient(ellipse 70% 45% at 36% 84%, rgba(0, 210, 255, 0.22) 0%, rgba(30, 107, 255, 0.12) 42%, transparent 75%)',
        }}
      />

      {/* 3. Subtle Wave Shimmer Sweep */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div
          className="absolute -bottom-10 left-0 w-[90vw] h-[55vh] animate-wave-shimmer"
          style={{
            background:
              'linear-gradient(90deg, transparent 0%, rgba(0, 210, 255, 0.08) 35%, rgba(255, 255, 255, 0.16) 50%, rgba(0, 210, 255, 0.08) 65%, transparent 100%)',
          }}
        />
      </div>

      {/* 4. Minimal Floating Light Particles along Wave Line */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <span
          className="absolute h-1.5 w-1.5 rounded-full bg-[#00D2FF] shadow-[0_0_8px_#00D2FF] animate-particle"
          style={{ left: '18%', top: '70%', animationDelay: '0s', animationDuration: '6.5s' }}
        />
        <span
          className="absolute h-1 w-1 rounded-full bg-white shadow-[0_0_6px_#00D2FF] animate-particle"
          style={{ left: '26%', top: '76%', animationDelay: '1.8s', animationDuration: '7.5s' }}
        />
        <span
          className="absolute h-2 w-2 rounded-full bg-[#38BDF8] shadow-[0_0_10px_#00D2FF] animate-particle"
          style={{ left: '34%', top: '68%', animationDelay: '3.2s', animationDuration: '8s' }}
        />
        <span
          className="absolute h-1.5 w-1.5 rounded-full bg-white shadow-[0_0_8px_#38BDF8] animate-particle"
          style={{ left: '42%', top: '74%', animationDelay: '4.5s', animationDuration: '7s' }}
        />
        <span
          className="absolute h-1 w-1 rounded-full bg-[#00D2FF] shadow-[0_0_6px_#00D2FF] animate-particle"
          style={{ left: '50%', top: '78%', animationDelay: '2.4s', animationDuration: '6.8s' }}
        />
        <span
          className="absolute h-2 w-2 rounded-full bg-[#60A5FA] shadow-[0_0_8px_#60A5FA] animate-particle"
          style={{ left: '58%', top: '72%', animationDelay: '5.2s', animationDuration: '7.8s' }}
        />
        <span
          className="absolute h-1.5 w-1.5 rounded-full bg-[#00D2FF] shadow-[0_0_8px_#00D2FF] animate-particle"
          style={{ left: '68%', top: '76%', animationDelay: '1.2s', animationDuration: '7.2s' }}
        />
      </div>

      {/* ===============================================================
          MAIN CONTENT GRID
          =============================================================== */}
      <div className="relative z-20 w-full max-w-6xl grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
        {/* Left Side: Crisp Mindful Metrics Branding */}
        <div className="lg:col-span-6 flex flex-col justify-center py-6 px-4 sm:px-8 text-center lg:text-left">
          <div className="max-w-md mx-auto lg:mx-0">
            <h1 className="text-[38px] sm:text-[46px] font-black tracking-tight text-[#0D192B] leading-[1.08]">
              Mindful Metrics
            </h1>
            <h2 className="mt-2 text-[30px] sm:text-[38px] font-extrabold tracking-tight bg-gradient-to-r from-[#0062FF] via-[#0095FF] to-[#00D2FF] bg-clip-text text-transparent leading-[1.12]">
              Wellbeing Intelligence
            </h2>
            <div className="mt-4 mx-auto lg:mx-0 h-1.5 w-24 rounded-full bg-gradient-to-r from-[#1E6BFF] via-[#00D2FF] to-transparent shadow-[0_0_12px_rgba(0,210,255,0.6)]" />
          </div>
        </div>

        {/* Right Side: The ONLY Login Card on the page */}
        <div className="lg:col-span-6 flex justify-center lg:justify-end">
          <form
            onSubmit={submit}
            className="w-full max-w-[420px] rounded-3xl border border-[#E2EAF2]/90 bg-white/95 backdrop-blur-md p-7 sm:p-9 shadow-[0_18px_45px_rgba(15,30,60,0.1)] transition-all"
          >
            <h2 className="text-[24px] font-bold text-[#0D192B] tracking-tight">Login</h2>

            {/* Email Field with Mail Icon */}
            <div className="mt-6">
              <label className="block text-[12px] font-semibold text-[#0D192B] mb-1.5">
                Email
              </label>
              <div className="relative flex items-center">
                <span className="absolute left-3.5 text-[#94A3B8]">
                  <Mail size={16} />
                </span>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@company.com"
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-[#E2EAF2] text-[13px] text-[#0D192B] bg-white outline-none transition focus:border-[#1E6BFF] focus:ring-2 focus:ring-[#1E6BFF]/15"
                  autoComplete="username"
                  required
                />
              </div>
            </div>

            {/* Password Field with Lock & Eye Toggle Icons */}
            <div className="mt-4">
              <label className="block text-[12px] font-semibold text-[#0D192B] mb-1.5">
                Password
              </label>
              <div className="relative flex items-center">
                <span className="absolute left-3.5 text-[#94A3B8]">
                  <Lock size={16} />
                </span>
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full pl-10 pr-10 py-2.5 rounded-xl border border-[#E2EAF2] text-[13px] text-[#0D192B] bg-white outline-none transition focus:border-[#1E6BFF] focus:ring-2 focus:ring-[#1E6BFF]/15"
                  autoComplete="current-password"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3.5 text-[#94A3B8] hover:text-[#0D192B] transition"
                  aria-label="Toggle password visibility"
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {/* Remember me & Forgot Password */}
            <div className="mt-3.5 flex items-center justify-between text-[12px]">
              <label className="flex items-center gap-2 cursor-pointer font-medium text-[#64748B]">
                <input
                  type="checkbox"
                  checked={remember}
                  onChange={(e) => setRemember(e.target.checked)}
                  className="h-4 w-4 rounded border-[#CBD5E1] text-[#1E6BFF] focus:ring-[#1E6BFF]"
                />
                <span>Remember me</span>
              </label>
              <button
                type="button"
                className="font-medium text-[#1E6BFF] hover:underline"
                onClick={() => alert('Password reset is managed by your organization HR.')}
              >
                Forgot password?
              </button>
            </div>

            {/* Error banner */}
            {error && (
              <div className="mt-3 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-[12px] font-medium text-rose-600">
                {error}
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="btn-primary mt-6 w-full py-3 rounded-xl text-[14px] font-semibold shadow-[0_6px_18px_rgba(30,107,255,0.3)] hover:shadow-[0_8px_24px_rgba(30,107,255,0.4)] disabled:opacity-75 disabled:cursor-not-allowed"
            >
              {loading ? (isWaking ? 'Waking Up Server...' : 'Signing In...') : 'Sign In'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
