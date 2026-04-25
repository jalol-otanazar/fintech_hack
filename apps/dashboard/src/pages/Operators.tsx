import React from 'react';
import { useOperatorStats } from '../hooks/useApi';

function Badge({ value, good = 70 }: { value: number; good?: number }) {
  const color = value >= good ? 'text-green-400' : value >= good * 0.6 ? 'text-amber-400' : 'text-red-400';
  return <span className={`font-semibold ${color}`}>{value}</span>;
}

export default function Operators() {
  const { data = [], isLoading } = useOperatorStats();

  if (isLoading) return <div className="text-slate-400 text-sm">Yuklanmoqda…</div>;

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">Operatorlar Statistikasi</h2>

      <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-700 text-slate-300 text-xs uppercase tracking-wide">
            <tr>
              <th className="px-4 py-3 text-left">Operator</th>
              <th className="px-4 py-3 text-left">Filial</th>
              <th className="px-4 py-3 text-right">Qo'ng'iroqlar</th>
              <th className="px-4 py-3 text-right">Sifat (o'rt.)</th>
              <th className="px-4 py-3 text-right">Guardrail</th>
              <th className="px-4 py-3 text-right">Taklif qabul</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700">
            {(data as any[]).map((op, i) => (
              <tr key={i} className="hover:bg-slate-750 transition-colors">
                <td className="px-4 py-3 font-medium text-white">{op.name}</td>
                <td className="px-4 py-3 text-slate-400">{op.branch_name}</td>
                <td className="px-4 py-3 text-right text-slate-300">{op.total_calls ?? 0}</td>
                <td className="px-4 py-3 text-right">
                  <Badge value={parseFloat(op.avg_quality ?? 0)} />
                </td>
                <td className="px-4 py-3 text-right text-slate-300">{op.total_guardrails ?? 0}</td>
                <td className="px-4 py-3 text-right text-slate-300">{op.offers_accepted ?? 0}</td>
              </tr>
            ))}
            {data.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-slate-500">Ma'lumot yo'q</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
