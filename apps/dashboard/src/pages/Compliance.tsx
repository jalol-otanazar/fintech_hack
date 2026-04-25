import React from 'react';
import { useCompliance } from '../hooks/useApi';

export default function Compliance() {
  const { data = [], isLoading } = useCompliance();

  if (isLoading) return <div className="text-slate-400 text-sm">Yuklanmoqda…</div>;

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">
        🛡️ Compliance Jurnali
        <span className="ml-2 text-sm font-normal text-orange-400">
          ({(data as any[]).length} ta ogohlantirish)
        </span>
      </h2>

      <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-700 text-slate-300 text-xs uppercase tracking-wide">
            <tr>
              <th className="px-4 py-3 text-left">Vaqt</th>
              <th className="px-4 py-3 text-left">Qo'ng'iroq ID</th>
              <th className="px-4 py-3 text-left">Bloklangan ibora</th>
              <th className="px-4 py-3 text-left">Tavsiya etilgan</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700">
            {(data as any[]).map((ev: any, i: number) => (
              <tr key={i} className="hover:bg-slate-750">
                <td className="px-4 py-3 text-slate-400 whitespace-nowrap text-xs">
                  {ev.fired_at ? new Date(ev.fired_at).toLocaleString('uz-UZ') : '—'}
                </td>
                <td className="px-4 py-3 text-slate-400 font-mono text-xs">
                  {ev.call_id?.substring(0, 10)}…
                </td>
                <td className="px-4 py-3">
                  <span className="bg-red-900 text-red-300 px-2 py-0.5 rounded text-xs">
                    {ev.blocked}
                  </span>
                </td>
                <td className="px-4 py-3 text-green-400 text-xs">{ev.replacement}</td>
              </tr>
            ))}
            {data.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-slate-500">
                  Ogohlantirish yo'q ✅
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
