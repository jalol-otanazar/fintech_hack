// apps/overlay/src/components/StressIcon.tsx
export function StressIcon() {
  return (
    <div className="fixed bottom-8 right-3 flex flex-col items-center gap-1 animate-pulse z-50"
         title="Operator stress detected">
      <span className="text-xl">💨</span>
      <span className="text-[9px] text-blue-400 font-semibold">Sekin gapiring</span>
    </div>
  );
}
