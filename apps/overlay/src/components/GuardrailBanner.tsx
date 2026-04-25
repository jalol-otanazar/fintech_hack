// apps/overlay/src/components/GuardrailBanner.tsx
import { GuardrailAlert } from '../../../shared/types/models';

interface Props { alert: GuardrailAlert; onDismiss: () => void }

export function GuardrailBanner({ alert, onDismiss }: Props) {
  return (
    <div className="animate-slide-down flex items-start gap-3 bg-orange-900/90 border border-orange-500 px-3 py-2 text-xs z-50">
      <span className="text-orange-300 font-bold flex-shrink-0">⚠️ Compliance</span>
      <div className="flex-1">
        <span className="text-orange-200 line-through mr-2">"{alert.blocked}"</span>
        <span className="text-green-300">→ "{alert.replacement}"</span>
      </div>
      <button onClick={onDismiss} className="text-orange-400 hover:text-white ml-2 font-bold">✕</button>
    </div>
  );
}
