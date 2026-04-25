import React from 'react';
import { useFlagged } from '../hooks/useApi';

const OUTCOME_LABEL: Record<string, string> = {
  accepted:  'Qabul qilindi',
  interested:'Qiziqdi',
  rejected:  'Rad etdi',
  escalated: 'Eskalyatsiya',
};

export default function Flagged() {
  const { data = [], isLoading } = useFlagged();

  if (isLoading) return <div className="text-slate-400 text-sm">Yuklanmoqda…</div>;

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">
        🚩 Tekshiruv Talab Qiladi
        <span className="ml-2 text-sm font-normal text-amber-400">
          ({(data as any[]).length} ta qo'ng'iroq)
        </span>
      </h2>
      <p className="text-xs text-slate-400">Sifat &lt;60 yoki guardrail fired bo'lgan qo'ng'iroqlar</p>

      <div className="space-y-2">
        {(data as any[]).map((c: any, i: number) => (
          <div key={i} className="bg-slate-800 border border-slate-700 rounded-xl p-4 flex items-center gap-4">
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white truncate">
                {c.id?.substring(0, 12)}… · {c.branch_name}
              </p>
              <p className="text-xs text-slate-400 mt-0.5">
                {c.created_at ? new Date(c.created_at).toLocaleString('uz-UZ') : '—'} ·{' '}
                KYC: {c.kyc_done ?? 0}/{c.kyc_total ?? 8} ·{' '}
                Guardrail: {c.guardrail_count ?? 0}
              </p>
              {c.summary_text && (
                <p className="text-xs text-slate-500 mt-1 italic truncate">{c.summary_text}</p>
              )}
            </div>
            <div className="text-right flex-shrink-0 space-y-1">
              <span
                className={`inline-block px-2 py-0.5 rounded-full text-xs font-semibold ${
                  (c.quality_score ?? 0) >= 60
                    ? 'bg-amber-900 text-amber-300'
                    : 'bg-red-900 text-red-300'
                }`}
              >
                {c.quality_score ?? '—'}/100
              </span>
              <p className="text-xs text-slate-400">
                {OUTCOME_LABEL[c.outcome] ?? c.outcome}
              </p>
            </div>
          </div>
        ))}
        {data.length === 0 && (
          <p className="text-slate-500 text-sm">Tekshiruv talab qiladigan qo'ng'iroqlar yo'q ✅</p>
        )}
      </div>
    </div>
  );
}
