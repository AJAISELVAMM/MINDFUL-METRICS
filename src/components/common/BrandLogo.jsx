export default function BrandLogo({
  size = 36,
  showText = true,
  dark = false,
  subtitle = 'Wellbeing Intelligence',
  className = '',
}) {
  return (
    <div className={`flex items-center gap-2.5 ${className}`}>
      <div
        className="relative flex shrink-0 items-center justify-center rounded-xl overflow-hidden transition-transform duration-200 hover:scale-105"
        style={{ width: size, height: size }}
      >
        <img
          src="/mindful-metrics-logo.png"
          alt="Mindful Metrics Logo"
          className="h-full w-full object-contain"
        />
      </div>
      {showText && (
        <div className="min-w-0">
          <p
            className={`text-[14px] font-bold tracking-tight leading-tight ${
              dark ? 'text-white' : 'text-[#0D192B]'
            }`}
          >
            Mindful Metrics
          </p>
          {subtitle && (
            <p
              className={`text-[10px] tracking-wide font-medium leading-none mt-0.5 ${
                dark ? 'text-white/60' : 'text-[#64748B]'
              }`}
            >
              {subtitle}
            </p>
          )}
        </div>
      )}
    </div>
  )
}
