import React from 'react';
import { useOperatorStats } from '../hooks/useApi';

const MEDALS = ['🥇', '🥈', '🥉'];

export default function Leaderboard() {
  const { data = [], isLoading } = useOperatorStats();

  if (isLoading) return <div className="text-slate-400 text-sm">Yuklanmoqda…</div>;

  const sorted = [...(data as any[])].sort(
    (a, b) => (parseFloat(b.avg_quality) || 0) - (parseFloat(a.avg_quality) || 0)
  );

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">🏆 Sifat Reytingi</h2>

      <div className="space-y-2">
        {sorted.map((op: any, i: number) => {
          const pct = Math.min(parseFloat(op.avg_quality) || 0, 100);
          const barColor = pct >= 70 ? 'bg-green-500' : pct >= 50 ? 'bg-amber-500' : 'bg-red-500';
          return (
            <div
              key={i}
              className={`bg-slate-800 border rounded-xl p-4 flex items-center gap-4 ${
                i === 0 ? 'border-yellow-500' : 'border-slate-700'
              }`}
            >
              <span className="text-2xl w-8 text-center">{MEDALS[i] ?? `#${i + 1}`}</span>
              <div className="flex-1 min-w-0">
                <div className="flex justify-between items-center">
                  <p className="text-sm font-semibold text-white">{op.name}</p>
                  <p className="text-sm font-bold text-white">{pct.toFixed(1)}/100</p>
                </div>
                <p className="text-xs text-slate-400 mb-2">{op.branch_name}</p>
                <div className="w-full bg-slate-700 rounded-full h-1.5">
                  <div
                    className={`${barColor} h-1.5 rounded-full transition-all`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
              <div className="text-right text-xs text-slate-400 flex-shrink-0">
                <p>{op.total_calls ?? 0} ta</p>
                <p>{op.offers_accepted ?? 0} qabul</p>
              </div>
            </div>
          );
        })}
        {sorted.length === 0 && (
          <p className="text-slate-500 text-sm">Ma'lumot yo'q</p>
        )}
      </div>
    </div>
  );
}
