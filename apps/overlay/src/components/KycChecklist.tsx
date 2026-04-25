// apps/overlay/src/components/KycChecklist.tsx
import { KYC_ITEMS, KycItem, KycStatus } from '../../../shared/types/models';

const STATUS_ICON: Record<KycStatus, string> = {
  PENDING:   '⬜',
  DETECTED:  '⏳',
  CONFIRMED: '✅',
};
const STATUS_COLOR: Record<KycStatus, string> = {
  PENDING:   'text-gray-500',
  DETECTED:  'text-yellow-400',
  CONFIRMED: 'text-green-400',
};
const LABELS: Record<KycItem, string> = {
  identity_confirmed:       'Shaxs tasdiqlandi',
  purpose_of_funds:         "Mablag' maqsadi",
  source_of_income:         'Daromad manbai',
  pep_screening:            'PEP tekshiruvi',
  aml_acknowledgment:       'AML tasdiqlash',
  product_terms_explained:  'Mahsulot shartlari',
  consent_recorded:         'Ruxsat olish',
  next_steps_communicated:  'Keyingi qadamlar',
};

interface Props { kyc?: Record<KycItem, KycStatus>; className?: string }

export function KycChecklist({ kyc, className = '' }: Props) {
  const items = kyc ?? Object.fromEntries(KYC_ITEMS.map(k => [k, 'PENDING' as KycStatus])) as Record<KycItem, KycStatus>;
  const done  = KYC_ITEMS.filter(k => items[k] === 'CONFIRMED').length;
  const pct   = Math.round(done / KYC_ITEMS.length * 100);
  const warn  = pct < 60;

  return (
    <div className={`flex flex-col bg-gray-900 border-l border-gray-800 ${className}`}>
      <div className="px-2 py-1 text-[10px] text-gray-500 font-semibold uppercase tracking-wider border-b border-gray-800">
        KYC Nazorat
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {KYC_ITEMS.map(item => (
          <div key={item} className={`flex items-center gap-1.5 text-xs ${STATUS_COLOR[items[item]]}`}>
            <span className="text-sm">{STATUS_ICON[items[item]]}</span>
            <span className="leading-tight">{LABELS[item]}</span>
            {item === 'pep_screening' && items[item] !== 'CONFIRMED' && (
              <span className="text-red-500">⚠️</span>
            )}
          </div>
        ))}
      </div>
      <div className={`px-2 py-1 text-[10px] border-t border-gray-800 font-semibold ${warn ? 'text-red-400' : 'text-green-400'}`}>
        Bajarildi: {pct}% {warn ? '⚠️' : ''}
      </div>
    </div>
  );
}
