import { useState } from 'react'
import { Copy, Check, AlertTriangle, Cpu } from 'lucide-react'
import ConfidenceBadge from './ConfidenceBadge'

const FIELD_CONFIG = {
  care_of:       { label: 'Care of',      emoji: '👤' },
  house_number:  { label: 'House / Flat', emoji: '🏠' },
  building_name: { label: 'Building',     emoji: '🏢' },
  street:        { label: 'Street',       emoji: '🛣️' },
  locality:      { label: 'Locality',     emoji: '📍' },
  landmark:      { label: 'Landmark',     emoji: '🗺️' },
  village:       { label: 'Village',      emoji: '🏘️' },
  subdistrict:   { label: 'Subdistrict',  emoji: '📌' },
  district:      { label: 'District',     emoji: '🗾' },
  city:          { label: 'City',         emoji: '🌆' },
  state:         { label: 'State',        emoji: '📋' },
  pincode:       { label: 'PIN Code',     emoji: '📮' },
}

const METHOD_LABELS = {
  pincode:    { label: 'PIN lookup',  color: 'text-emerald-400' },
  exact:      { label: 'Exact match', color: 'text-blue-400' },
  fuzzy:      { label: 'Fuzzy match', color: 'text-yellow-400' },
  state_abbr: { label: 'State abbr.', color: 'text-orange-400' },
  none:       { label: 'No match',    color: 'text-red-400' },
}

export default function ParseResult({ data }) {
  const [copied, setCopied] = useState(false)

  const parsed   = data.parsed || {}
  const confidence = parsed.confidence_score ?? 0
  const errors   = parsed.validation_errors ?? []
  const method   = parsed.match_method ?? 'none'

  const addressFields = Object.entries(FIELD_CONFIG).filter(
    ([key]) => parsed[key] != null && parsed[key] !== ''
  )

  function copyJSON() {
    navigator.clipboard.writeText(JSON.stringify(parsed, null, 2))
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="bg-white/[0.03] border border-white/10 rounded-2xl p-5 space-y-5">

      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-[10px] text-white/30 font-mono uppercase tracking-widest mb-1">
            Input
          </p>
          <p className="text-sm text-white/70 font-mono break-all leading-relaxed">
            {data.original}
          </p>
        </div>
        <button
          onClick={copyJSON}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-white/5 hover:bg-white/10
                     border border-white/10 text-white/50 hover:text-white text-xs
                     font-medium rounded-lg transition-all duration-200 shrink-0"
        >
          {copied
            ? <><Check size={12} className="text-emerald-400" /> Copied</>
            : <><Copy size={12} /> Copy JSON</>
          }
        </button>
      </div>

      <hr className="border-white/5" />

      {/* Confidence + method */}
      <div className="flex items-center gap-3 flex-wrap">
        <ConfidenceBadge score={confidence} />
        <div className="flex items-center gap-1.5 text-xs text-white/30">
          <Cpu size={12} />
          <span>Resolved via</span>
          <span className={`font-medium ${METHOD_LABELS[method]?.color ?? 'text-white/40'}`}>
            {METHOD_LABELS[method]?.label ?? method}
          </span>
        </div>
        {data.request_id && (
          <span className="ml-auto text-xs text-white/20 font-mono">
            #{data.request_id}
          </span>
        )}
      </div>

      {/* Fields grid */}
      {addressFields.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {addressFields.map(([key, cfg]) => (
            <div
              key={key}
              className="flex items-center gap-3 bg-white/[0.03] border border-white/[0.06]
                         rounded-xl px-3 py-2.5"
            >
              <span className="text-lg shrink-0">{cfg.emoji}</span>
              <div className="min-w-0">
                <p className="text-[10px] text-white/30 uppercase tracking-widest">
                  {cfg.label}
                </p>
                <p className="text-sm text-white font-medium truncate">
                  {parsed[key]}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Warnings */}
      {errors.length > 0 && (
        <div className="space-y-1.5">
          {errors.map((err, i) => (
            <div
              key={i}
              className="flex items-start gap-2 px-3 py-2 bg-yellow-500/5
                         border border-yellow-500/10 rounded-lg"
            >
              <AlertTriangle size={12} className="mt-0.5 shrink-0 text-yellow-400" />
              <span className="text-xs text-yellow-300/70">{err}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}