// apps/overlay/src/components/CallHeader.tsx
interface Props {
  callId: string | null; callStart: number | null;
  lang: 'uz' | 'ru'; onToggleLang: () => void;
}
export function CallHeader({ callId, callStart, lang, onToggleLang }: Props) {
  const elapsed = callStart ? Math.floor((Date.now() - callStart) / 1000) : 0;
  const mm = String(Math.floor(elapsed / 60)).padStart(2,'0');
  const ss = String(elapsed % 60).padStart(2,'0');
  return (
    <div className="flex items-center gap-4 px-3 py-1.5 bg-gray-900 border-b border-gray-800 text-xs">
      <span className="flex items-center gap-1.5">
        <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
        <span className="font-semibold text-red-400">JONLI</span>
      </span>
      <span className="text-gray-400">Mijoz: <span className="text-white">{callId ?? '—'}</span></span>
      <span className="text-gray-500">⏱ {mm}:{ss}</span>
      <button onClick={onToggleLang}
        className="ml-auto px-2 py-0.5 rounded bg-gray-700 hover:bg-gray-600 font-mono font-bold tracking-widest">
        {lang.toUpperCase()}
      </button>
    </div>
  );
}
