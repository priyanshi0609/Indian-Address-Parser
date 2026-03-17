export default function ConfidenceBadge({ score }) {
  const pct = Math.round(score * 100)

  const config =
    score >= 0.8
      ? {
          label: 'High confidence',
          bar: 'bg-emerald-500',
          text: 'text-emerald-400',
          bg: 'bg-emerald-500/10 border border-emerald-500/20',
        }
      : score >= 0.5
      ? {
          label: 'Medium confidence',
          bar: 'bg-yellow-500',
          text: 'text-yellow-400',
          bg: 'bg-yellow-500/10 border border-yellow-500/20',
        }
      : {
          label: 'Low confidence',
          bar: 'bg-red-500',
          text: 'text-red-400',
          bg: 'bg-red-500/10 border border-red-500/20',
        }

  return (
    <div className={`inline-flex items-center gap-3 px-3 py-2 rounded-lg ${config.bg}`}>
      <div className="w-24 h-1.5 bg-white/10 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ${config.bar}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={`text-sm font-semibold tabular-nums ${config.text}`}>
        {pct}%
      </span>
      <span className="text-xs text-white/30">{config.label}</span>
    </div>
  )
}