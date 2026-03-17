import { useState, useEffect, useCallback } from 'react'
import { useAuth, useUser } from '@clerk/clerk-react'
import Navbar from '../components/Navbar'
import AddressInput from '../components/AddressInput'
import ParseResult from '../components/ParseResult'
import HistoryPanel from '../components/HistoryPanel'
import { parseAddress, fetchHistory } from '../api/client'
import { History } from 'lucide-react'

export default function Dashboard() {
  const { userId } = useAuth()
  const { user }   = useUser()

  const [result,         setResult]         = useState(null)
  const [loading,        setLoading]        = useState(false)
  const [error,          setError]          = useState(null)
  const [history,        setHistory]        = useState([])
  const [historyLoading, setHistoryLoading] = useState(true)
  const [selected,       setSelected]       = useState(null)
  const [sidebarOpen,    setSidebarOpen]    = useState(false)

  const loadHistory = useCallback(async () => {
    setHistoryLoading(true)
    try {
      const data = await fetchHistory(userId, 30, 0)
      setHistory(data.results || [])
    } catch {
      // non-critical
    } finally {
      setHistoryLoading(false)
    }
  }, [userId])

  useEffect(() => { loadHistory() }, [loadHistory])

  async function handleParse(address) {
    setLoading(true)
    setError(null)
    setResult(null)
    setSelected(null)
    try {
      const data = await parseAddress(address, userId)
      setResult(data)
      loadHistory()
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        'Could not connect to the backend. Make sure the API is running.'
      )
    } finally {
      setLoading(false)
    }
  }

  function handleSelectHistory(item) {
    setSelected(item)
    setResult({
      request_id: item.id,
      original:   item.raw_address,
      parsed:     item.parsed_output,
    })
    setError(null)
    setSidebarOpen(false)
  }

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white flex flex-col">
      <Navbar />

      <div className="flex flex-1 overflow-hidden">

        {/* Sidebar — desktop */}
        <aside className="hidden md:flex w-72 border-r border-white/5 flex-col shrink-0">
          <div className="p-4 border-b border-white/5">
            <h2 className="text-xs font-semibold text-white/40 uppercase tracking-widest">
              Your History
            </h2>
          </div>
          <div className="flex-1 overflow-y-auto">
            <HistoryPanel
              items={history}
              loading={historyLoading}
              selectedId={selected?.id}
              onSelect={handleSelectHistory}
            />
          </div>
        </aside>

        {/* Mobile sidebar overlay */}
        {sidebarOpen && (
          <div className="fixed inset-0 z-20 md:hidden">
            <div
              className="absolute inset-0 bg-black/60"
              onClick={() => setSidebarOpen(false)}
            />
            <aside className="absolute left-0 top-0 bottom-0 w-72 bg-[#0d0d14]
                              border-r border-white/5 flex flex-col z-30">
              <div className="p-4 border-b border-white/5 flex items-center justify-between">
                <h2 className="text-xs font-semibold text-white/40 uppercase tracking-widest">
                  Your History
                </h2>
                <button
                  onClick={() => setSidebarOpen(false)}
                  className="text-white/40 hover:text-white text-lg leading-none"
                >
                  ×
                </button>
              </div>
              <div className="flex-1 overflow-y-auto">
                <HistoryPanel
                  items={history}
                  loading={historyLoading}
                  selectedId={selected?.id}
                  onSelect={handleSelectHistory}
                />
              </div>
            </aside>
          </div>
        )}

        {/* Main */}
        <main className="flex-1 overflow-y-auto">
          <div className="max-w-3xl mx-auto px-4 md:px-6 py-8 md:py-10">

            {/* Top bar with mobile history button */}
            <div className="flex items-center justify-between mb-6">
              <div>
                <h1 className="text-xl md:text-2xl font-bold text-white">
                  Welcome back{user?.firstName ? `, ${user.firstName}` : ''}
                </h1>
                <p className="text-sm text-white/40 mt-0.5">
                  Paste any Indian address — structured output instantly.
                </p>
              </div>
              <button
                onClick={() => setSidebarOpen(true)}
                className="md:hidden flex items-center gap-2 px-3 py-2 bg-white/5
                           border border-white/10 rounded-lg text-white/60 text-sm"
              >
                <History size={14} />
                History
              </button>
            </div>

            {/* Input */}
            <AddressInput onParse={handleParse} loading={loading} />

            {/* Error */}
            {error && (
              <div className="mt-4 p-4 rounded-xl bg-red-500/10 border border-red-500/20
                              text-red-300 text-sm">
                {error}
              </div>
            )}

            {/* Result */}
            {result && !error && (
              <div className="mt-6">
                <ParseResult data={result} />
              </div>
            )}

            {/* Empty state */}
            {!result && !loading && !error && (
              <div className="mt-20 text-center">
                <div className="w-16 h-16 rounded-2xl bg-white/[0.03] border border-white/5
                                flex items-center justify-center mx-auto mb-4">
                  <span className="text-3xl">📍</span>
                </div>
                <p className="text-sm text-white/20">
                  Enter an address above to see the structured output
                </p>
              </div>
            )}

          </div>
        </main>
      </div>
    </div>
  )
}