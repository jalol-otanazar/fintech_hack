import React from 'react';
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import Overview    from './pages/Overview';
import Operators   from './pages/Operators';
import Flagged     from './pages/Flagged';
import Leaderboard from './pages/Leaderboard';
import Compliance  from './pages/Compliance';

const NAV = [
  { to: '/',            label: '📊 Umumiy' },
  { to: '/operators',   label: '👤 Operatorlar' },
  { to: '/flagged',     label: '🚩 Tekshiruv' },
  { to: '/leaderboard', label: '🏆 Reyting' },
  { to: '/compliance',  label: '🛡️ Compliance' },
];

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen bg-slate-900 text-slate-100">
        {/* Sidebar */}
        <aside className="w-52 flex-shrink-0 bg-slate-800 border-r border-slate-700 flex flex-col">
          <div className="px-4 py-5 border-b border-slate-700">
            <h1 className="text-lg font-bold text-blue-400">BankCopilot</h1>
            <p className="text-xs text-slate-400 mt-0.5">Manager Dashboard</p>
          </div>
          <nav className="flex-1 py-4 space-y-1 px-2">
            {NAV.map(({ to, label }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                className={({ isActive }) =>
                  `block px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-blue-600 text-white'
                      : 'text-slate-300 hover:bg-slate-700 hover:text-white'
                  }`
                }
              >
                {label}
              </NavLink>
            ))}
          </nav>
          <div className="px-4 py-3 border-t border-slate-700 text-xs text-slate-500">
            Har 30s yangilanadi
          </div>
        </aside>

        {/* Main content */}
        <main className="flex-1 overflow-y-auto p-6">
          <Routes>
            <Route path="/"            element={<Overview />} />
            <Route path="/operators"   element={<Operators />} />
            <Route path="/flagged"     element={<Flagged />} />
            <Route path="/leaderboard" element={<Leaderboard />} />
            <Route path="/compliance"  element={<Compliance />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
