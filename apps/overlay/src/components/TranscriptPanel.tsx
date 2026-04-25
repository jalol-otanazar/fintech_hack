// apps/overlay/src/components/TranscriptPanel.tsx
import { useRef, useEffect } from 'react';
import { TranscriptWord } from '../../../shared/types/models';

const SPEAKER_COLOR: Record<string, string> = {
  operator: 'text-blue-400',
  customer: 'text-green-400',
};
const LANG_BADGE: Record<string, string> = {
  uz: 'bg-orange-800 text-orange-200',
  ru: 'bg-blue-800 text-blue-200',
  mixed: 'bg-purple-800 text-purple-200',
};

interface Props { words: TranscriptWord[]; className?: string }

export function TranscriptPanel({ words, className = '' }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [words]);

  // Group consecutive words by same speaker into lines
  const lines: { speaker: string; lang: string; text: string }[] = [];
  for (const w of words) {
    const last = lines[lines.length - 1];
    if (last && last.speaker === w.speaker) {
      last.text += ' ' + w.text;
    } else {
      lines.push({ speaker: w.speaker, lang: w.lang, text: w.text });
    }
  }

  return (
    <div className={`flex flex-col bg-gray-900 border-r border-gray-800 overflow-y-auto ${className}`}>
      <div className="px-2 py-1 text-[10px] text-gray-500 font-semibold uppercase tracking-wider border-b border-gray-800">
        Transkripsiya
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-1 text-xs">
        {lines.map((l, i) => (
          <div key={i} className="flex flex-col gap-0.5">
            <div className="flex items-center gap-1">
              <span className={`font-semibold ${SPEAKER_COLOR[l.speaker]}`}>
                [{l.speaker === 'operator' ? 'O' : 'M'}]
              </span>
              <span className={`text-[9px] px-1 rounded ${LANG_BADGE[l.lang]}`}>{l.lang.toUpperCase()}</span>
            </div>
            <span className="text-gray-200 leading-tight">{l.text}</span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
