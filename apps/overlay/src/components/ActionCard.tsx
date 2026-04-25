// apps/overlay/src/components/ActionCard.tsx
import { useState, useEffect } from 'react';
import { TurnContext } from '../../../shared/types/models';

const MOMENTUM_COLOR = (m: number) =>
  m >= 0.7 ? 'border-green-500' : m >= 0.4 ? 'border-orange-500' : 'border-red-600';

const PERSONA_ICON: Record<string, string> = {
  formal: '🎩', casual: '👋', analytical: '📊', emotional: '💙',
};

interface Props {
  ctx: TurnContext | null; lang: 'uz' | 'ru';
  onUsed: (id: string) => void; className?: string;
}

export function ActionCard({ ctx, lang, onUsed, className = '' }: Props) {
  const [dismissed, setDismissed] = useState(false);
  const [renderTime, setRenderTime] = useState<number>(0);

  const nbo = ctx?.nbo;

  useEffect(() => {
    if (nbo) { setDismissed(false); setRenderTime(Date.now()); }
  }, [nbo?.card_id]);

  // Keyboard: Space = used, Esc = dismiss
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (!nbo || dismissed) return;
      if (e.code === 'Space') { onUsed(nbo.card_id); setDismissed(true); }
      if (e.key === 'Escape') setDismissed(true);
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [nbo, dismissed, onUsed]);

  return (
    <div className={`flex flex-col bg-gray-950 p-3 ${className}`}>
      <div className="text-[10px] text-gray-500 font-semibold uppercase tracking-wider mb-2">
        Keyingi Harakat
      </div>

      {!nbo || dismissed ? (
        <div className="flex-1 flex items-center justify-center text-gray-600 text-xs">
          {ctx?.momentum !== undefined && ctx.momentum < 0.4
            ? '🔴 Momentum past — qayta jalb qilish kerak'
            : ctx?.momentum !== undefined && ctx.momentum < 0.7
            ? '🟡 Taklif qilish uchun momentum yetarli emas'
            : 'Tahlil qilinmoqda…'}
        </div>
      ) : (
        <div className={`border-l-4 ${MOMENTUM_COLOR(ctx?.momentum ?? 0)} pl-3 flex flex-col gap-2`}>
          <div className="flex items-start justify-between gap-2">
            <span className="text-sm font-bold text-white leading-tight">{nbo.headline}</span>
            <span className="text-lg">{PERSONA_ICON[nbo.persona]}</span>
          </div>
          <p className="text-xs text-gray-300 leading-snug">{nbo.body}</p>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-[10px] text-gray-500 capitalize">[{nbo.persona}]</span>
            <span className="text-[10px] text-green-400 font-semibold">
              {Math.round(nbo.confidence * 100)}%
            </span>
            <div className="flex-1" />
            <button onClick={() => setDismissed(true)}
              className="text-[10px] px-2 py-0.5 rounded bg-gray-700 hover:bg-gray-600">
              O'tkazib yubor [Esc]
            </button>
            <button onClick={() => { onUsed(nbo.card_id); setDismissed(true); }}
              className="text-[10px] px-2 py-0.5 rounded bg-green-700 hover:bg-green-600 font-semibold">
              ✓ Ishlatdim [Space]
            </button>
          </div>
          {ctx?.objections?.length > 0 && (
            <div className="text-[10px] text-orange-400 mt-1">
              ← Objection: {ctx.objections.join(', ')}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
