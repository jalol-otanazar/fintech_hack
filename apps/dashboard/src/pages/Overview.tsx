import React from 'react';
import { useCalls, useOperatorStats } from '../hooks/useApi';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';

function KpiCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
      <p className="text-xs text-slate-400 uppercase tracking-wide">{label}</p>
      <p className="text-3xl font-bold text-white mt-1">{value}</p>
      {sub && <p className="text-xs text-slate-400 mt-1">{sub}</p>}
    </div>
  );
}

export default function Overview() {
  const { data: calls = [], isLoading: loadingCalls } = useCalls(200);
  const { data: ops   = [], isLoading: loadingOps   } = useOperatorStats();

  if (loadingCalls || loadingOps) {
    return <div className="text-slate-400 text-sm">Yuklanmoqda…</div>;
  }

  const totalCalls   = calls.length;
  const avgQuality   = calls.length
    ? (calls.reduce((s: number, c: any) => s + (c.quality_score ?? 0), 0) / calls.length).toFixed(1)
    : 0;
  const kycDoneAvg   = calls.length
    ? Math.round(calls.reduce((s: number, c: any) => s + (c.kyc_done ?? 0), 0) / calls.length * 100 / 8)
    : 0;
  const guardrailSum = calls.reduce((s: number, c: any) => s + (c.guardrail_count ?? 0), 0);

  // branch breakdown for chart
  const branchMap: Record<string, { quality: number[]; count: number }> = {};
  for (const c of calls as any[]) {
    if (!branchMap[c.branch_name]) branchMap[c.branch_name] = { quality: [], count: 0 };
    branchMap[c.branch_name].quality.push(c.quality_score ?? 0);
    branchMap[c.branch_name].count++;
  }
  const branchData = Object.entries(branchMap).map(([name, d]) => ({
    name: name.replace(' filiali', '').substring(0, 14),
    avg:  parseFloat((d.quality.reduce((a, b) => a + b, 0) / d.quality.length).toFixed(1)),
    calls: d.count,
  }));

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold">Umumiy Ko'rinish</h2>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard label="Jami qo'ng'iroqlar" value={totalCalls} />
        <KpiCard label="O'rtacha sifat" value={`${avgQuality}/100`} />
        <KpiCard label="KYC bajarilish" value={`${kycDoneAvg}%`} />
        <KpiCard label="Guardrail ogohlantirish" value={guardrailSum} sub="jami" />
      </div>

      <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
        <h3 className="text-sm font-semibold text-slate-300 mb-4">Filial bo'yicha o'rtacha sifat</h3>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={branchData} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
            <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} />
            <YAxis domain={[0, 100]} tick={{ fill: '#94a3b8', fontSize: 11 }} />
            <Tooltip
              contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
              labelStyle={{ color: '#e2e8f0' }}
            />
            <Bar dataKey="avg" radius={[4, 4, 0, 0]}>
              {branchData.map((d, i) => (
                <Cell key={i} fill={d.avg >= 70 ? '#22c55e' : d.avg >= 50 ? '#f59e0b' : '#ef4444'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
