// apps/overlay/src/App.tsx
import { useEffect, useRef, useReducer, useCallback } from 'react';
import { TurnContext, TranscriptWord, GuardrailAlert, WsMessage, KycItem } from '../../shared/types/models';
import { CallHeader }      from './components/CallHeader';
import { TranscriptPanel } from './components/TranscriptPanel';
import { ActionCard }      from './components/ActionCard';
import { KycChecklist }    from './components/KycChecklist';
import { MomentumBar }     from './components/MomentumBar';
import { GuardrailBanner } from './components/GuardrailBanner';
import { StressIcon }      from './components/StressIcon';

// ── State ────────────────────────────────────────────────────────────────────
interface AppState {
  callId:      string | null;
  callStart:   number | null;
  lang:        'uz' | 'ru';
  words:       TranscriptWord[];
  turnCtx:     TurnContext | null;
  guardrail:   GuardrailAlert | null;
  stress:      boolean;
  momentum:    number;
}

type Action =
  | { type: 'CALL_START'; callId: string }
  | { type: 'TRANSCRIPT'; words: TranscriptWord[] }
  | { type: 'TURN_CTX';  ctx: TurnContext }
  | { type: 'GUARDRAIL'; alert: GuardrailAlert }
  | { type: 'STRESS' }
  | { type: 'CLEAR_GUARDRAIL' }
  | { type: 'CLEAR_STRESS' }
  | { type: 'TOGGLE_LANG' };

function reducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case 'CALL_START':   return { ...state, callId: action.callId, callStart: Date.now(), words: [] };
    case 'TRANSCRIPT': {
      // Dedup: skip words whose ts_start already exists in state
      const existingTs = new Set(state.words.map(w => w.ts_start));
      const fresh = action.words.filter(w => !existingTs.has(w.ts_start));
      if (!fresh.length) return state;
      return { ...state, words: [...state.words, ...fresh].slice(-200) };
    }
    case 'TURN_CTX':     return { ...state, turnCtx: action.ctx, momentum: action.ctx.momentum };
    case 'GUARDRAIL':    return { ...state, guardrail: action.alert };
    case 'STRESS':       return { ...state, stress: true };
    case 'CLEAR_GUARDRAIL': return { ...state, guardrail: null };
    case 'CLEAR_STRESS': return { ...state, stress: false };
    case 'TOGGLE_LANG':  return { ...state, lang: state.lang === 'uz' ? 'ru' : 'uz' };
    default:             return state;
  }
}

const INITIAL: AppState = {
  callId: null, callStart: null, lang: 'uz',
  words: [], turnCtx: null, guardrail: null, stress: false, momentum: 0,
};

// ── App ──────────────────────────────────────────────────────────────────────
export default function App() {
  const [state, dispatch] = useReducer(reducer, INITIAL);
  const lastUpdate = useRef(0);

  // Debounce: max 2 UI updates/second
  const dispatchDebounced = useCallback((action: Action) => {
    const now = Date.now();
    if (now - lastUpdate.current < 500) return;
    lastUpdate.current = now;
    dispatch(action);
  }, []);

  useEffect(() => {
    const api = (window as any).electronAPI;
    if (!api) return;

    api.onBrainMessage((msg: WsMessage) => {
      switch (msg.type) {
        case 'call_start' as any:
          dispatch({ type: 'CALL_START', callId: (msg as any).payload.call_id });
          break;
        case 'transcript_chunk':
          dispatch({ type: 'TRANSCRIPT', words: msg.payload as any });
          break;
        case 'turn_context':
          dispatchDebounced({ type: 'TURN_CTX', ctx: msg.payload as TurnContext });
          break;
        case 'guardrail_alert':
          dispatch({ type: 'GUARDRAIL', alert: msg.payload as GuardrailAlert });
          setTimeout(() => dispatch({ type: 'CLEAR_GUARDRAIL' }), 8000);
          break;
        case 'operator_stress':
          dispatch({ type: 'STRESS' });
          setTimeout(() => dispatch({ type: 'CLEAR_STRESS' }), 15000);
          break;
      }
    });

    // Heartbeat every 10s
    const hb = setInterval(() => api.sendHeartbeat(), 10000);
    // Keyboard shortcuts
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'r' || e.key === 'R') dispatch({ type: 'TOGGLE_LANG' });
    };
    window.addEventListener('keydown', onKey);
    return () => { clearInterval(hb); window.removeEventListener('keydown', onKey); };
  }, [dispatchDebounced]);

  return (
    <div className="bg-gray-950 text-gray-100 h-screen flex flex-col select-none font-sans">
      {state.guardrail && (
        <GuardrailBanner alert={state.guardrail} onDismiss={() => dispatch({ type: 'CLEAR_GUARDRAIL' })} />
      )}
      <CallHeader callId={state.callId} callStart={state.callStart} lang={state.lang}
        onToggleLang={() => dispatch({ type: 'TOGGLE_LANG' })} />

      <div className="flex flex-1 overflow-hidden">
        <TranscriptPanel words={state.words} className="w-64 flex-shrink-0" />
        <ActionCard ctx={state.turnCtx} lang={state.lang}
          onUsed={(id) => (window as any).electronAPI?.sendCardUsed(id)}
          className="flex-1" />
        <KycChecklist kyc={state.turnCtx?.kyc} className="w-52 flex-shrink-0" />
      </div>

      <MomentumBar momentum={state.momentum} />
      {state.stress && <StressIcon />}
    </div>
  );
}
