import { Route, Routes } from 'react-router-dom'
import History from './pages/History'
import Home from './pages/Home'
import ShoppingSession from './pages/ShoppingSession'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/session/:id" element={<ShoppingSession />} />
      <Route path="/history" element={<History />} />
      <Route path="*" element={<Home />} />
    </Routes>
  )
}
