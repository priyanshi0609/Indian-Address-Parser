import { Loader2 } from 'lucide-react'

function scoreColor(score) {
  if (score >= 0.8) return 'bg-emerald-500'
  if (score >= 0.5) return 'bg-yellow-500'
  return 'bg-red-500'
}

function timeAgo(isoString) {
  const diff = Date.now() - new Date(isoString).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1)  return 'Just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24)  return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

export default function HistoryPanel({ items, loading, selectedId, onSelect }) {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-12 text-white/20">
        <Loader2 size={18} className="animate-spin" />
      </div>
    )
  }

  if (!items.length) {
    return (
      <div className="p-6 text-center">
        <p className="text-xs text-white/20">No parses yet. Try one!</p>
      </div>
    )
  }

  return (
    <div className="py-2">
      {items.map((item) => {
        const p = item.parsed_output || {}
        const isSelected = selectedId === item.id
        return (
          <button
            key={item.id}
            onClick={() => onSelect(item)}
            className={`w-full text-left px-4 py-3 border-b border-white/5
                        hover:bg-white/[0.03] transition-colors
                        ${isSelected
                          ? 'bg-violet-500/10 border-l-2 border-l-violet-500'
                          : ''
                        }`}
          >
            <p className="text-xs text-white/70 font-mono truncate mb-1.5">
              {item.raw_address}
            </p>
            {(p.city || p.state) && (
              <p className="text-xs text-white/40 truncate mb-1.5">
                {[p.city, p.state].filter(Boolean).join(', ')}
              </p>
            )}
            <div className="flex items-center gap-2">
              <span className={`w-1.5 h-1.5 rounded-full ${scoreColor(item.confidence_score)}`} />
              <span className="text-[10px] text-white/20 tabular-nums">
                {Math.round(item.confidence_score * 100)}%
              </span>
              <span className="text-[10px] text-white/20 ml-auto">
                {timeAgo(item.created_at)}
              </span>
            </div>
          </button>
        )
      })}
    </div>
  )
}