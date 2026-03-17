import { useNavigate } from 'react-router-dom'
import { useAuth, SignInButton } from '@clerk/clerk-react'
import { MapPin, Zap, Shield, BarChart3, ArrowRight } from 'lucide-react'

const PROBLEMS = [
  { label: 'Fully structured',    value: 'H No 15/1, Indira Nagar, Lucknow, UP - 226016', color: 'text-emerald-400' },
  { label: 'No city or state',    value: 'Near Durga Mandir, Shahdara, 110032',             color: 'text-yellow-400' },
  { label: 'Abbreviations+typos', value: 'opp city mall, lknw UP 226016',                  color: 'text-orange-400' },
  { label: 'Stuck tokens',        value: '237okhlaphase3NewDelhi110001',                    color: 'text-red-400'    },
]

const OUTPUT = {
  locality: 'Shahdara',
  landmark: 'Near Durga Mandir',
  city:     'Delhi',
  district: 'East Delhi',
  state:    'Delhi',
  pincode:  '110032',
}

const FEATURES = [
  { icon: Zap,      title: 'PIN as Anchor',    desc: 'A 6-digit PIN maps to a unique post office area. We auto-fill city, district and state from it — even when the user never mentions them.' },
  { icon: MapPin,   title: '12 Structured Fields', desc: 'Extracts care-of, house number, building, street, locality, landmark, village, subdistrict, district, city, state and pincode.' },
  { icon: BarChart3,title: 'Confidence Score', desc: 'Every result gets a 0–1 score + missing field warnings so downstream systems know exactly how much to trust the output.' },
  { icon: Shield,   title: 'Handles Noise',    desc: 'Typos, abbreviations, concatenated tokens like "237okhlaphase3NewDelhi" — the normalisation pipeline handles all of it before extraction.' },
]

const STEPS = [
  { n: '01', title: 'Normalise',     desc: 'Expand abbreviations, split stuck tokens, remove noise' },
  { n: '02', title: 'Extract PIN',   desc: 'Find the 6-digit PIN — our primary anchor' },
  { n: '03', title: 'Enrich',        desc: 'PIN → city + district + state from 155k-entry dataset' },
  { n: '04', title: 'Extract fields',desc: 'Regex extractors for house, landmark, care-of, street' },
  { n: '05', title: 'Score',         desc: 'Weighted confidence score + missing field warnings' },
]

export default function Landing() {
  const { isSignedIn } = useAuth()
  const navigate = useNavigate()

  const CTAButton = () =>
    isSignedIn ? (
      <button
        onClick={() => navigate('/dashboard')}
        className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r
                   from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500
                   text-white font-semibold rounded-xl transition-all duration-200 text-sm"
      >
        Open Dashboard <ArrowRight size={16} />
      </button>
    ) : (
      <SignInButton mode="modal">
        <button className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r
                           from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500
                           text-white font-semibold rounded-xl transition-all duration-200 text-sm">
          Try it free <ArrowRight size={16} />
        </button>
      </SignInButton>
    )

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white">

      {/* Navbar */}
      <nav className="border-b border-white/5 px-6 py-4 flex items-center justify-between max-w-7xl mx-auto">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600
                          flex items-center justify-center">
            <MapPin size={16} className="text-white" />
          </div>
          <span className="font-semibold text-white">AddressParser</span>
        </div>
        <CTAButton />
      </nav>

      {/* Hero */}
      <section className="max-w-7xl mx-auto px-6 pt-24 pb-16 text-center">
        <div className="inline-flex items-center gap-2 bg-violet-500/10 border border-violet-500/20
                        rounded-full px-4 py-1.5 mb-8">
          <span className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-pulse" />
          <span className="text-violet-300 text-sm font-medium">Indian Address Intelligence</span>
        </div>

        <h1 className="text-4xl md:text-6xl lg:text-7xl font-bold tracking-tight mb-6 leading-tight">
          Unstructured address in.{' '}
          <span className="bg-gradient-to-r from-violet-400 to-indigo-400 bg-clip-text text-transparent">
            Structured JSON out.
          </span>
        </h1>

        <p className="text-lg text-white/50 max-w-2xl mx-auto mb-10 leading-relaxed">
          Indian addresses are inconsistent. Someone might write their full address,
          or just a landmark and a PIN code. This parser handles every format.
        </p>

        <div className="flex items-center justify-center gap-4 flex-wrap">
          <CTAButton />
          <a
            href="#how-it-works"
            className="inline-flex items-center gap-2 px-6 py-3 bg-white/5 hover:bg-white/10
                       border border-white/10 text-white/60 hover:text-white font-medium
                       rounded-xl transition-all duration-200 text-sm"
          >
            See how it works
          </a>
        </div>
      </section>

      {/* Before / After */}
      <section className="max-w-7xl mx-auto px-6 pb-24">
        <div className="grid md:grid-cols-2 gap-6">

          <div className="bg-white/[0.03] border border-white/8 rounded-2xl p-6">
            <p className="text-[10px] font-mono text-white/30 uppercase tracking-widest mb-5">
              The problem — addresses look like this
            </p>
            <div className="space-y-4">
              {PROBLEMS.map((p) => (
                <div key={p.label} className="flex items-start gap-3">
                  <span className={`text-xs font-mono mt-0.5 shrink-0 ${p.color}`}>
                    {p.label}
                  </span>
                  <code className="text-sm text-white/60 font-mono break-all">{p.value}</code>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-white/[0.03] border border-white/8 rounded-2xl p-6">
            <p className="text-[10px] font-mono text-white/30 uppercase tracking-widest mb-5">
              The output — "Near Durga Mandir, Shahdara, 110032"
            </p>
            <pre className="text-sm font-mono text-white/70 leading-relaxed">
{`{
${Object.entries(OUTPUT).map(([k,v]) => `  "${k}": "${v}",`).join('\n')}
  "confidence_score": 0.75,
  "match_method": "pincode"
}`}
            </pre>
            <div className="mt-4 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-yellow-400" />
              <span className="text-xs text-white/30">
                City, district, state inferred from PIN — user never mentioned them
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="border-t border-white/5 py-24">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-14">
            <h2 className="text-3xl font-bold mb-3">How it works</h2>
            <p className="text-white/40 max-w-lg mx-auto text-sm">
              A 5-step pipeline converts raw text into structured data.
            </p>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            {STEPS.map((s) => (
              <div key={s.n}
                   className="bg-white/[0.03] border border-white/5 rounded-2xl p-4 text-center">
                <span className="text-3xl font-bold text-white/5 block">{s.n}</span>
                <h3 className="font-semibold text-sm mt-2 mb-1 text-white">{s.title}</h3>
                <p className="text-xs text-white/30 leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-24 border-t border-white/5">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-5">
            {FEATURES.map((f) => {
              const Icon = f.icon
              return (
                <div key={f.title}
                     className="bg-white/[0.03] border border-white/5 rounded-2xl p-5 group
                                hover:border-violet-500/20 transition-colors duration-200">
                  <div className="w-10 h-10 rounded-xl bg-violet-500/10 group-hover:bg-violet-500/20
                                  flex items-center justify-center mb-4 transition-colors duration-200">
                    <Icon size={20} className="text-violet-400" />
                  </div>
                  <h3 className="font-semibold text-sm mb-2 text-white">{f.title}</h3>
                  <p className="text-xs text-white/40 leading-relaxed">{f.desc}</p>
                </div>
              )
            })}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-24 border-t border-white/5">
        <div className="max-w-xl mx-auto px-6 text-center">
          <h2 className="text-3xl font-bold mb-3">Ready to parse?</h2>
          <p className="text-white/40 text-sm mb-8">
            Sign in to start parsing addresses. Your history is saved and accessible any time.
          </p>
          <CTAButton />
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/5 py-6">
        <div className="max-w-7xl mx-auto px-6 flex items-center justify-between
                        text-white/20 text-xs">
          <span>Indian Address Parser</span>
          <span>FastAPI · PostgreSQL · React</span>
        </div>
      </footer>
    </div>
  )
}