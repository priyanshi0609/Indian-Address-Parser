import { useState } from 'react'
import { Loader2, Sparkles, Shuffle } from 'lucide-react'

const EXAMPLES = [
  'S/O Ram Singh, H No 15/1 Near City Mall, Indira Nagar, Lucknow, UP - 226016',
  'Near Durga Mandir, Shahdara, 110032',
  'Vill Rampur, Post Kunda, Dist Pratapgarh, UP - 230143',
  'Flat 4B, Sector 18, Noida, Uttar Pradesh - 201301',
  '237okhlaphase3NewDelhi110001',
]

export default function AddressInput({ onParse, loading }) {
  const [address, setAddress] = useState('')

  function handleSubmit(e) {
    e.preventDefault()
    if (address.trim().length < 5) return
    onParse(address.trim())
  }

  function loadExample() {
    const pick = EXAMPLES[Math.floor(Math.random() * EXAMPLES.length)]
    setAddress(pick)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <textarea
        value={address}
        onChange={(e) => setAddress(e.target.value)}
        placeholder="Paste any Indian address here…"
        rows={4}
        disabled={loading}
        className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3
                   text-white placeholder-white/20 text-sm font-mono resize-none
                   focus:outline-none focus:border-violet-500/50 focus:bg-white/[0.07]
                   transition-all duration-200 disabled:opacity-50"
      />

      <div className="flex gap-3">
        <button
          type="submit"
          disabled={loading || address.trim().length < 5}
          className="flex-1 flex items-center justify-center gap-2 px-5 py-2.5
                     bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500
                     hover:to-indigo-500 text-white text-sm font-semibold rounded-xl
                     transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {loading ? (
            <>
              <Loader2 size={15} className="animate-spin" />
              Parsing…
            </>
          ) : (
            <>
              <Sparkles size={15} />
              Parse Address
            </>
          )}
        </button>

        <button
          type="button"
          onClick={loadExample}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2.5 bg-white/5 hover:bg-white/10
                     border border-white/10 text-white/60 hover:text-white text-sm
                     font-medium rounded-xl transition-all duration-200 disabled:opacity-40"
        >
          <Shuffle size={14} />
          Example
        </button>
      </div>
    </form>
  )
}