import { useNavigate } from 'react-router-dom'
import { UserButton } from '@clerk/clerk-react'
import { MapPin } from 'lucide-react'

export default function Navbar() {
  const navigate = useNavigate()

  return (
    <header className="h-14 border-b border-white/5 flex items-center justify-between px-6 shrink-0 bg-[#0a0a0f]/80 backdrop-blur-sm sticky top-0 z-10">
      <button
        onClick={() => navigate('/')}
        className="flex items-center gap-2 hover:opacity-80 transition-opacity"
      >
        <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center">
          <MapPin size={14} className="text-white" />
        </div>
        <span className="font-semibold text-sm text-white">AddressParser</span>
      </button>
      <UserButton afterSignOutUrl="/" />
    </header>
  )
}