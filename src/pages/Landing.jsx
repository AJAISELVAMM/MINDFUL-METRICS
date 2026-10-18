import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Menu,
  X,
  TrendingUp,
  ShieldCheck,
  HeartHandshake,
  Activity,
  CalendarCheck,
  BrainCircuit,
  MessageSquare,
  Sparkles,
  Mail,
  Building,
  CheckCircle2,
} from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import BrandLogo from '../components/common/BrandLogo'

export default function Landing() {
  const { user } = useAuth()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [contactSubmitted, setContactSubmitted] = useState(false)

  const dashPath = user
    ? user.role === 'manager'
      ? '/manager/dashboard'
      : user.role === 'hr'
      ? '/hr/dashboard'
      : '/employee/dashboard'
    : null

  return (
    <div className="relative min-h-screen bg-gradient-to-b from-[#FFFFFF] via-[#F4F9FD] to-[#E9F3FC] text-[#0D192B] overflow-x-hidden selection:bg-[#1E6BFF]/20 selection:text-[#1E6BFF]">
      {/* Background Soft Ambient Glow & Flowing Arc Orbs */}
      <div className="pointer-events-none absolute -top-20 -left-20 h-[520px] w-[520px] rounded-full bg-[#1E6BFF]/8 blur-[120px]" />
      <div className="pointer-events-none absolute top-1/4 right-0 h-[600px] w-[600px] rounded-full bg-[#00D2FF]/12 blur-[140px]" />
      <div className="pointer-events-none absolute top-3/4 left-1/4 h-[450px] w-[450px] rounded-full bg-[#38BDF8]/10 blur-[100px]" />

      {/* Decorative Curving Gradient Sweep behind Hero */}
      <div className="pointer-events-none absolute top-0 right-0 w-[65vw] h-[85vh] max-w-[960px] opacity-70 overflow-hidden">
        <svg
          viewBox="0 0 1000 800"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="w-full h-full"
        >
          <path
            d="M200 800 C 400 650, 650 500, 800 200 C 880 50, 950 -50, 1000 -100"
            stroke="url(#arcGlow1)"
            strokeWidth="120"
            strokeLinecap="round"
            opacity="0.25"
          />
          <path
            d="M300 800 C 500 680, 750 520, 900 220"
            stroke="url(#arcGlow2)"
            strokeWidth="2"
            strokeDasharray="6 8"
            opacity="0.4"
          />
          <defs>
            <linearGradient id="arcGlow1" x1="200" y1="800" x2="1000" y2="-100" gradientUnits="userSpaceOnUse">
              <stop stopColor="#00D2FF" />
              <stop offset="0.5" stopColor="#38BDF8" />
              <stop offset="1" stopColor="#1E6BFF" />
            </linearGradient>
            <linearGradient id="arcGlow2" x1="300" y1="800" x2="900" y2="220" gradientUnits="userSpaceOnUse">
              <stop stopColor="#00D2FF" />
              <stop offset="1" stopColor="#1E6BFF" />
            </linearGradient>
          </defs>
        </svg>
      </div>

      {/* Navigation Header */}
      <header className="relative z-30 mx-auto max-w-7xl px-6 py-6 md:px-12 flex items-center justify-between">
        {/* Left: Brand Logo */}
        <Link to="/" className="inline-block transition-transform hover:opacity-95">
          <BrandLogo size={38} subtitle="Wellbeing Intelligence" />
        </Link>

        {/* Center: Navigation Links */}
        <nav className="hidden md:flex items-center gap-8">
          <a
            href="#home"
            className="relative text-[14px] font-semibold text-[#0D192B] pb-1 hover:text-[#1E6BFF] transition-colors"
          >
            Home
            <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#1E6BFF] rounded-full" />
          </a>
          <a
            href="#about"
            className="text-[14px] font-medium text-[#64748B] hover:text-[#0D192B] transition-colors"
          >
            About
          </a>
          <a
            href="#features"
            className="text-[14px] font-medium text-[#64748B] hover:text-[#0D192B] transition-colors"
          >
            Features
          </a>
          <a
            href="#contact"
            className="text-[14px] font-medium text-[#64748B] hover:text-[#0D192B] transition-colors"
          >
            Contact
          </a>
        </nav>

        {/* Right: Actions - ONLY Login button */}
        <div className="hidden md:flex items-center">
          {dashPath ? (
            <Link
              to={dashPath}
              className="px-6 py-2 rounded-full text-[13px] font-semibold text-white bg-[#1E6BFF] hover:bg-[#1557DB] transition-all shadow-sm"
            >
              Dashboard
            </Link>
          ) : (
            <Link
              to="/login"
              className="px-6 py-2 rounded-full text-[13px] font-semibold text-[#1E6BFF] border border-[#93C5FD] bg-white hover:bg-[#EFF6FF] hover:border-[#1E6BFF] transition-all shadow-sm"
            >
              Login
            </Link>
          )}
        </div>

        {/* Mobile Hamburger Toggle */}
        <div className="md:hidden flex items-center">
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="rounded-xl border border-[#CBD5E1] bg-white p-2.5 text-[#0D192B] shadow-sm"
            aria-label="Toggle menu"
          >
            {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </header>

      {/* Mobile Drawer Menu */}
      {mobileMenuOpen && (
        <div className="relative z-40 md:hidden bg-white/95 backdrop-blur-md border-b border-[#E2EAF2] px-6 py-4 space-y-3 shadow-lg">
          <a
            href="#home"
            onClick={() => setMobileMenuOpen(false)}
            className="block text-[14px] font-semibold text-[#1E6BFF] py-1"
          >
            Home
          </a>
          <a
            href="#about"
            onClick={() => setMobileMenuOpen(false)}
            className="block text-[14px] font-medium text-[#64748B] py-1"
          >
            About
          </a>
          <a
            href="#features"
            onClick={() => setMobileMenuOpen(false)}
            className="block text-[14px] font-medium text-[#64748B] py-1"
          >
            Features
          </a>
          <a
            href="#contact"
            onClick={() => setMobileMenuOpen(false)}
            className="block text-[14px] font-medium text-[#64748B] py-1"
          >
            Contact
          </a>
          <div className="pt-2">
            <Link
              to={dashPath || '/login'}
              onClick={() => setMobileMenuOpen(false)}
              className="block text-center py-2.5 rounded-full text-[13px] font-semibold text-[#1E6BFF] border border-[#93C5FD] bg-white"
            >
              {dashPath ? 'Dashboard' : 'Login'}
            </Link>
          </div>
        </div>
      )}

      {/* =============================================================== */}
      {/* HERO SECTION (#home) - Faithful to Reference Inspiration */}
      {/* =============================================================== */}
      <main id="home" className="relative z-10 mx-auto max-w-7xl px-6 pt-6 pb-20 md:pt-12 md:pb-28 md:px-12">
        <div className="grid grid-cols-1 items-center gap-12 lg:grid-cols-12 lg:gap-8">
          {/* Left Column: Hero Content */}
          <div className="lg:col-span-6 xl:col-span-6">
            {/* Eyebrow Pill */}
            <div className="inline-flex items-center gap-2 rounded-full border border-[#DBEAFE] bg-[#EFF6FF] px-4 py-1.5 text-[11px] font-bold tracking-wider text-[#1E6BFF] shadow-sm uppercase">
              <span>Healthier People. Stronger Workplaces.</span>
            </div>

            {/* Main Headline */}
            <h1 className="mt-6 text-[44px] font-black tracking-tight text-[#0A1629] leading-[1.08] sm:text-[54px] lg:text-[66px]">
              Wellbeing,
              <br />
              understood.
              <br />
              <span className="bg-gradient-to-r from-[#0062FF] via-[#0095FF] to-[#00D2FF] bg-clip-text text-transparent">
                Work, improved.
              </span>
            </h1>

            {/* Subtitle */}
            <p className="mt-6 max-w-lg text-[16px] md:text-[18px] leading-relaxed text-[#64748B]">
              AI-powered workplace insights to understand workload, wellbeing, and burnout risk using real workplace data.
            </p>

            {/* Bottom Value Badges (from Reference Image) */}
            <div className="mt-10 flex flex-wrap items-center gap-3 text-[13px] sm:text-[14px] font-medium text-[#64748B]">
              <span>People-first insights</span>
              <span className="h-1.5 w-1.5 rounded-full bg-[#00D2FF]" />
              <span>Responsible AI</span>
              <span className="h-1.5 w-1.5 rounded-full bg-[#00D2FF]" />
              <span>Better workdays</span>
            </div>
          </div>

          {/* Right Column: Hero Graphic with Circular Portrait, Concentric Orbits, and Floating Analytics */}
          <div className="relative lg:col-span-6 xl:col-span-6 flex justify-center lg:justify-end">
            <div className="relative w-full max-w-[500px]">
              {/* Outer Concentric Cyan Glowing Ring & Orbits */}
              <div className="absolute inset-0 -m-6 sm:-m-10 rounded-full border border-[#00D2FF]/25 pointer-events-none" />
              <div className="absolute inset-0 -m-12 sm:-m-16 rounded-full border border-[#38BDF8]/15 pointer-events-none" />

              {/* Decorative Accent Orbiting Dots */}
              <div className="absolute -top-3 right-1/4 h-3.5 w-3.5 rounded-full bg-[#00D2FF] shadow-[0_0_12px_#00D2FF] pointer-events-none z-20" />
              <div className="absolute bottom-12 -left-4 h-3 w-3 rounded-full bg-[#1E6BFF] shadow-[0_0_10px_#1E6BFF] pointer-events-none z-20" />
              <div className="absolute top-1/2 -right-6 h-4 w-4 rounded-full bg-white border-2 border-[#00D2FF] shadow-sm pointer-events-none z-20" />

              {/* Dot-matrix Grid Accents */}
              <div className="absolute -top-6 -left-6 w-24 h-24 opacity-35 pointer-events-none">
                <svg viewBox="0 0 100 100" fill="#1E6BFF" className="w-full h-full">
                  <circle cx="10" cy="10" r="2" />
                  <circle cx="30" cy="10" r="2" />
                  <circle cx="50" cy="10" r="2" />
                  <circle cx="70" cy="10" r="2" />
                  <circle cx="90" cy="10" r="2" />
                  <circle cx="10" cy="30" r="2" />
                  <circle cx="30" cy="30" r="2" />
                  <circle cx="50" cy="30" r="2" />
                  <circle cx="70" cy="30" r="2" />
                  <circle cx="90" cy="30" r="2" />
                  <circle cx="10" cy="50" r="2" />
                  <circle cx="30" cy="50" r="2" />
                  <circle cx="50" cy="50" r="2" />
                  <circle cx="70" cy="50" r="2" />
                  <circle cx="90" cy="50" r="2" />
                </svg>
              </div>

              {/* Ambient Glow behind Portrait */}
              <div className="absolute inset-0 m-auto h-[380px] w-[380px] rounded-full bg-gradient-to-tr from-[#00D2FF]/20 via-[#38BDF8]/15 to-[#1E6BFF]/15 blur-2xl pointer-events-none" />

              {/* Main Circular Portrait Frame */}
              <div className="relative z-10 mx-auto aspect-square w-[320px] sm:w-[380px] md:w-[410px] overflow-hidden rounded-full border-[5px] border-white bg-gradient-to-b from-[#E0F2FE] to-[#BAE6FD] shadow-[0_24px_50px_rgba(15,30,60,0.12)]">
                <img
                  src="/hero-woman-hd.jpg"
                  alt="Mindful Metrics Workplace Wellbeing"
                  className="h-full w-full object-cover object-top scale-105"
                  onError={(e) => {
                    e.currentTarget.src = '/hero-woman.png'
                  }}
                />
              </div>

              {/* Floating Glassmorphic Card 1: Top-Left "Workplace Insights" (Wave Trend) */}
              <div className="absolute -top-4 -left-2 sm:top-2 sm:-left-8 z-20 w-[190px] sm:w-[220px] rounded-2xl border border-white/80 bg-white/85 p-3.5 sm:p-4 shadow-[0_16px_36px_rgba(15,30,60,0.12)] backdrop-blur-xl">
                <div className="flex items-center gap-2 mb-2.5">
                  <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-[#EFF6FF] text-[#1E6BFF]">
                    <TrendingUp size={14} strokeWidth={2.5} />
                  </div>
                  <span className="text-[12px] sm:text-[13px] font-bold text-[#0D192B]">
                    Workplace Insights
                  </span>
                </div>
                {/* Clean SVG Area Wave Trend Chart */}
                <div className="relative w-full h-14 sm:h-16">
                  <svg viewBox="0 0 160 60" fill="none" className="w-full h-full">
                    <path
                      d="M0 45 C 25 45, 35 22, 60 28 C 85 34, 95 10, 120 18 C 140 24, 150 14, 160 12 L 160 60 L 0 60 Z"
                      fill="url(#waveGrad)"
                      opacity="0.5"
                    />
                    <path
                      d="M0 45 C 25 45, 35 22, 60 28 C 85 34, 95 10, 120 18 C 140 24, 150 14, 160 12"
                      stroke="#00D2FF"
                      strokeWidth="2.5"
                      strokeLinecap="round"
                    />
                    <circle cx="120" cy="18" r="3.5" fill="#00D2FF" stroke="#FFFFFF" strokeWidth="2" />
                    <defs>
                      <linearGradient id="waveGrad" x1="0" y1="0" x2="0" y2="60" gradientUnits="userSpaceOnUse">
                        <stop stopColor="#00D2FF" />
                        <stop offset="1" stopColor="#FFFFFF" stopOpacity="0" />
                      </linearGradient>
                    </defs>
                  </svg>
                </div>
                {/* Metric pill row */}
                <div className="mt-2 flex items-center justify-between text-[10px] text-[#64748B] font-medium pt-1.5 border-t border-[#F1F5F9]">
                  <span className="h-1.5 w-10 bg-[#E2E8F0] rounded-full" />
                  <span className="h-1.5 w-14 bg-[#CBD5E1] rounded-full" />
                  <span className="h-1.5 w-8 bg-[#93C5FD] rounded-full" />
                </div>
              </div>

              {/* Floating Glassmorphic Card 2: Bottom-Right (Segmented Radial Donut & Status Indicators) */}
              <div className="absolute -bottom-4 -right-2 sm:bottom-4 sm:-right-8 z-20 w-[190px] sm:w-[220px] rounded-2xl border border-white/80 bg-white/85 p-3.5 sm:p-4 shadow-[0_16px_36px_rgba(15,30,60,0.12)] backdrop-blur-xl">
                <div className="flex items-center gap-3">
                  {/* SVG Segmented Donut Chart */}
                  <div className="relative h-12 w-12 sm:h-14 sm:w-14 shrink-0">
                    <svg viewBox="0 0 42 42" className="w-full h-full -rotate-90">
                      <circle cx="21" cy="21" r="15.9" fill="transparent" stroke="#E2E8F0" strokeWidth="5" />
                      <circle
                        cx="21"
                        cy="21"
                        r="15.9"
                        fill="transparent"
                        stroke="#00D2FF"
                        strokeWidth="5"
                        strokeDasharray="65 35"
                        strokeDashoffset="0"
                        strokeLinecap="round"
                      />
                      <circle
                        cx="21"
                        cy="21"
                        r="15.9"
                        fill="transparent"
                        stroke="#1E6BFF"
                        strokeWidth="5"
                        strokeDasharray="25 75"
                        strokeDashoffset="-68"
                        strokeLinecap="round"
                      />
                    </svg>
                  </div>
                  {/* Legend / Status Indicators */}
                  <div className="space-y-1.5 flex-1">
                    <div className="flex items-center gap-1.5">
                      <span className="h-2 w-2 rounded-full bg-[#00D2FF]" />
                      <span className="h-1.5 w-full bg-[#E2E8F0] rounded-full" />
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="h-2 w-2 rounded-full bg-[#1E6BFF]" />
                      <span className="h-1.5 w-3/4 bg-[#E2E8F0] rounded-full" />
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="h-2 w-2 rounded-full bg-[#93C5FD]" />
                      <span className="h-1.5 w-1/2 bg-[#E2E8F0] rounded-full" />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* =============================================================== */}
      {/* ABOUT SECTION (#about) */}
      {/* =============================================================== */}
      <section id="about" className="relative z-10 mx-auto max-w-7xl px-6 py-20 md:py-28 md:px-12 border-t border-[#E2EAF2]/60">
        <div className="max-w-2xl">
          <div className="inline-flex items-center gap-2 rounded-full border border-[#DBEAFE] bg-[#EFF6FF] px-3.5 py-1 text-[11px] font-bold tracking-wider text-[#1E6BFF] uppercase">
            <span>About The Platform</span>
          </div>
          <h2 className="mt-4 text-[32px] sm:text-[40px] font-extrabold tracking-tight text-[#0D192B] leading-tight">
            Built for empathy, backed by intelligence.
          </h2>
          <p className="mt-4 text-[16px] text-[#64748B] leading-relaxed">
            Mindful Metrics combines workload signals, working hours, and voluntary wellness pulses to help organizations foster resilient teams without intrusive surveillance.
          </p>
        </div>

        <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="rounded-2xl border border-[#E2EAF2] bg-white p-7 shadow-sm hover:shadow-md transition">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-[#EFF6FF] text-[#1E6BFF]">
              <ShieldCheck size={24} />
            </div>
            <h3 className="mt-5 text-[18px] font-bold text-[#0D192B]">Privacy-First Design</h3>
            <p className="mt-2.5 text-[14px] text-[#64748B] leading-relaxed">
              Confidentiality is fundamental. Employees receive personal reflections, while organizational leaders access high-level patterns to support work-life balance.
            </p>
          </div>

          <div className="rounded-2xl border border-[#E2EAF2] bg-white p-7 shadow-sm hover:shadow-md transition">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-[#ECFDF5] text-[#10B981]">
              <HeartHandshake size={24} />
            </div>
            <h3 className="mt-5 text-[18px] font-bold text-[#0D192B]">Proactive Support</h3>
            <p className="mt-2.5 text-[14px] text-[#64748B] leading-relaxed">
              Detect prolonged workload pressure early so managers and employees can realign deliverables, plan recovery time, and prevent burnout before it escalates.
            </p>
          </div>

          <div className="rounded-2xl border border-[#E2EAF2] bg-white p-7 shadow-sm hover:shadow-md transition">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-[#F0F9FF] text-[#0284C7]">
              <BrainCircuit size={24} />
            </div>
            <h3 className="mt-5 text-[18px] font-bold text-[#0D192B]">Responsible AI Guidance</h3>
            <p className="mt-2.5 text-[14px] text-[#64748B] leading-relaxed">
              Actionable recommendations generated from verified workload metrics and role-specific surveys, empowering leaders with constructive insights.
            </p>
          </div>
        </div>
      </section>

      {/* =============================================================== */}
      {/* FEATURES SECTION (#features) */}
      {/* =============================================================== */}
      <section id="features" className="relative z-10 mx-auto max-w-7xl px-6 py-20 md:py-28 md:px-12 border-t border-[#E2EAF2]/60">
        <div className="text-center max-w-2xl mx-auto">
          <div className="inline-flex items-center gap-2 rounded-full border border-[#DBEAFE] bg-[#EFF6FF] px-3.5 py-1 text-[11px] font-bold tracking-wider text-[#1E6BFF] uppercase">
            <span>Core Capabilities</span>
          </div>
          <h2 className="mt-4 text-[32px] sm:text-[40px] font-extrabold tracking-tight text-[#0D192B] leading-tight">
            Comprehensive wellbeing intelligence.
          </h2>
          <p className="mt-3 text-[15px] sm:text-[16px] text-[#64748B]">
            Every layer of the platform is designed to connect attendance, task distribution, and feedback into a coherent view.
          </p>
        </div>

        <div className="mt-14 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="rounded-2xl border border-[#E2EAF2] bg-white p-6 shadow-sm hover:border-[#1E6BFF]/40 transition">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#EFF6FF] text-[#1E6BFF]">
              <Activity size={20} />
            </div>
            <h4 className="mt-4 text-[16px] font-bold text-[#0D192B]">Predictive Burnout Risk</h4>
            <p className="mt-2 text-[13px] text-[#64748B] leading-relaxed">
              Machine learning models evaluate multi-day workload trends, overtime patterns, and task urgency to gauge fatigue risk.
            </p>
          </div>

          <div className="rounded-2xl border border-[#E2EAF2] bg-white p-6 shadow-sm hover:border-[#1E6BFF]/40 transition">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#F0FDF4] text-[#16A34A]">
              <MessageSquare size={20} />
            </div>
            <h4 className="mt-4 text-[16px] font-bold text-[#0D192B]">Daily Pulse Surveys</h4>
            <p className="mt-2 text-[13px] text-[#64748B] leading-relaxed">
              Lightweight daily reflections allow team members to register stress levels and task manageability in seconds.
            </p>
          </div>

          <div className="rounded-2xl border border-[#E2EAF2] bg-white p-6 shadow-sm hover:border-[#1E6BFF]/40 transition">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#FAF5FF] text-[#9333EA]">
              <CalendarCheck size={20} />
            </div>
            <h4 className="mt-4 text-[16px] font-bold text-[#0D192B]">Attendance & Leave Harmony</h4>
            <p className="mt-2 text-[13px] text-[#64748B] leading-relaxed">
              Clear check-in rules, half-day sessions, and time-off tracking help teams avoid chronic overwork and schedule recovery.
            </p>
          </div>

          <div className="rounded-2xl border border-[#E2EAF2] bg-white p-6 shadow-sm hover:border-[#1E6BFF]/40 transition">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#FFF7ED] text-[#EA580C]">
              <Sparkles size={20} />
            </div>
            <h4 className="mt-4 text-[16px] font-bold text-[#0D192B]">Actionable Interventions</h4>
            <p className="mt-2 text-[13px] text-[#64748B] leading-relaxed">
              Structured managerial review workflows give leaders recommended steps for redistributing deliverables safely.
            </p>
          </div>
        </div>
      </section>

      {/* =============================================================== */}
      {/* CONTACT SECTION (#contact) */}
      {/* =============================================================== */}
      <section id="contact" className="relative z-10 mx-auto max-w-7xl px-6 py-20 md:py-28 md:px-12 border-t border-[#E2EAF2]/60">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-center">
          <div className="lg:col-span-6">
            <div className="inline-flex items-center gap-2 rounded-full border border-[#DBEAFE] bg-[#EFF6FF] px-3.5 py-1 text-[11px] font-bold tracking-wider text-[#1E6BFF] uppercase">
              <span>Contact Us</span>
            </div>
            <h2 className="mt-4 text-[32px] sm:text-[40px] font-extrabold tracking-tight text-[#0D192B] leading-tight">
              Ready to cultivate a healthier workplace?
            </h2>
            <p className="mt-4 text-[16px] text-[#64748B] leading-relaxed max-w-md">
              Learn how Mindful Metrics can be configured for your organization. Connect with our workplace analytics team.
            </p>

            <div className="mt-8 space-y-4 text-[14px] text-[#0D192B]">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#EFF6FF] text-[#1E6BFF]">
                  <Mail size={18} />
                </div>
                <span className="font-medium text-[#64748B]">support@mindfulmetrics.internal</span>
              </div>
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#EFF6FF] text-[#1E6BFF]">
                  <Building size={18} />
                </div>
                <span className="font-medium text-[#64748B]">Enterprise Wellbeing & Analytics Platform</span>
              </div>
            </div>
          </div>

          <div className="lg:col-span-6">
            <div className="rounded-3xl border border-[#E2EAF2] bg-white p-7 sm:p-9 shadow-sm">
              {contactSubmitted ? (
                <div className="text-center py-8">
                  <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-[#ECFDF5] text-[#10B981]">
                    <CheckCircle2 size={26} />
                  </div>
                  <h3 className="mt-4 text-[18px] font-bold text-[#0D192B]">Message Received</h3>
                  <p className="mt-2 text-[14px] text-[#64748B]">
                    Thank you for reaching out. An analytics advisor will follow up with your organization.
                  </p>
                </div>
              ) : (
                <form
                  onSubmit={(e) => {
                    e.preventDefault()
                    setContactSubmitted(true)
                  }}
                  className="space-y-4"
                >
                  <h3 className="text-[18px] font-bold text-[#0D192B]">Inquire About Deployment</h3>
                  <div>
                    <label className="block text-[12px] font-semibold text-[#0D192B] mb-1">
                      Full Name
                    </label>
                    <input
                      type="text"
                      required
                      placeholder="Your name"
                      className="w-full px-4 py-2.5 rounded-xl border border-[#E2EAF2] text-[13px] text-[#0D192B] outline-none transition focus:border-[#1E6BFF] focus:ring-2 focus:ring-[#1E6BFF]/15"
                    />
                  </div>
                  <div>
                    <label className="block text-[12px] font-semibold text-[#0D192B] mb-1">
                      Work Email
                    </label>
                    <input
                      type="email"
                      required
                      placeholder="you@company.com"
                      className="w-full px-4 py-2.5 rounded-xl border border-[#E2EAF2] text-[13px] text-[#0D192B] outline-none transition focus:border-[#1E6BFF] focus:ring-2 focus:ring-[#1E6BFF]/15"
                    />
                  </div>
                  <div>
                    <label className="block text-[12px] font-semibold text-[#0D192B] mb-1">
                      Organization Message
                    </label>
                    <textarea
                      rows={3}
                      required
                      placeholder="Tell us about your team size and wellbeing objectives..."
                      className="w-full px-4 py-2.5 rounded-xl border border-[#E2EAF2] text-[13px] text-[#0D192B] outline-none transition focus:border-[#1E6BFF] focus:ring-2 focus:ring-[#1E6BFF]/15 resize-none"
                    />
                  </div>
                  <button
                    type="submit"
                    className="w-full py-3 rounded-xl text-[14px] font-semibold text-white bg-[#1E6BFF] hover:bg-[#1557DB] transition shadow-sm"
                  >
                    Submit Inquiry
                  </button>
                </form>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="relative z-10 border-t border-[#E2EAF2] bg-white py-10 px-6 md:px-12 text-center sm:text-left">
        <div className="mx-auto max-w-7xl flex flex-col sm:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-3">
            <BrandLogo size={28} subtitle="" />
            <span className="text-[13px] text-[#64748B]">
              © {new Date().getFullYear()} Mindful Metrics. All rights reserved.
            </span>
          </div>

          <div className="flex items-center gap-6 text-[13px] text-[#64748B]">
            <a href="#home" className="hover:text-[#0D192B] transition-colors">
              Home
            </a>
            <a href="#about" className="hover:text-[#0D192B] transition-colors">
              About
            </a>
            <a href="#features" className="hover:text-[#0D192B] transition-colors">
              Features
            </a>
            <a href="#contact" className="hover:text-[#0D192B] transition-colors">
              Contact
            </a>
          </div>
        </div>
      </footer>
    </div>
  )
}
