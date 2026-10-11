import { Link, Route, Routes } from 'react-router-dom'
import History from './pages/History'
import Home from './pages/Home'
import ShoppingSession from './pages/ShoppingSession'

export default function App() {
  return (
    <div className="min-h-screen bg-[radial-gradient(60rem_30rem_at_50%_-10%,rgba(91,124,250,0.18),transparent)]">
      <nav className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-6">
        <Link to="/" className="flex items-center gap-2 font-bold text-white">
          <img src="/favicon.svg" alt="" className="h-7 w-7" />
          CartMind
        </Link>
        <Link to="/history" className="text-sm text-slate-300 hover:text-white">
          History
        </Link>
      </nav>
      <main className="mx-auto max-w-7xl px-4 pb-16 pt-4 sm:px-6">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/session/:id" element={<ShoppingSession />} />
          <Route path="/history" element={<History />} />
          <Route path="*" element={<p className="text-slate-400">Page not found.</p>} />
        </Routes>
      </main>
    </div>
  )
}
