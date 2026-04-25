// apps/overlay/src/components/MomentumBar.tsx
interface Props { momentum: number }

export function MomentumBar({ momentum }: Props) {
  const pct   = Math.round(momentum * 100);
  const color = momentum >= 0.7 ? '#22c55e' : momentum >= 0.4 ? '#f97316' : '#ef4444';
  const label = momentum >= 0.7
    ? '🟢 Taklif qilish vaqti keldi'
    : momentum >= 0.4
    ? '🟡 Mijozni jalb qilishda davom eting'
    : '🔴 Qayta bog\'lanish skriptini ishlating';

  return (
    <div className="px-3 py-1.5 bg-gray-900 border-t border-gray-800 flex items-center gap-3">
      <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider w-20">Momentum</span>
      <div className="flex-1 h-2 bg-gray-700 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700 ease-out"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
      <span className="text-xs font-bold w-8 text-right" style={{ color }}>{pct}%</span>
      <span className="text-[10px] text-gray-400 hidden md:block">{label}</span>
    </div>
  );
}
