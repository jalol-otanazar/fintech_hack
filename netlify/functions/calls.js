// netlify/functions/calls.js
// Returns demo call data — no DB needed for web demo
// API key is NEVER sent to the browser

const BRANCHES = [
  'Yunusobod filiali', 'Chilonzor filiali', 'Mirzo Ulugbek filiali',
  'Sergeli filiali', 'Olmazor filiali', 'Shayxontohur filiali',
];
const OUTCOMES = ['accepted', 'interested', 'rejected', 'escalated'];
const PERSONAS = ['formal', 'casual', 'analytical', 'emotional'];

function rnd(min, max) { return Math.floor(Math.random() * (max - min + 1)) + min; }
function pick(arr) { return arr[Math.floor(Math.random() * arr.length)]; }

function makeCalls(seed, limit = 50, offset = 0) {
  // Deterministic pseudo-random so data is consistent per request
  let s = seed + offset;
  const calls = [];
  for (let i = 0; i < limit; i++) {
    s = (s * 1664525 + 1013904223) & 0xffffffff;
    const quality = 40 + Math.abs(s % 61);        // 40–100
    const kyc_done = Math.abs((s >> 4) % 9);       // 0–8
    const guardrail = quality < 60 ? Math.abs((s >> 8) % 4) : 0;
    const ts = new Date(Date.now() - Math.abs((s >> 12) % (30 * 86400 * 1000)));
    calls.push({
      id: `call-${(s >>> 0).toString(16).padStart(8, '0')}-${i + offset}`,
      branch_name: BRANCHES[Math.abs((s >> 16) % BRANCHES.length)],
      operator_id: `op-${Math.abs((s >> 20) % 8) + 1}`,
      quality_score: quality,
      kyc_done,
      kyc_total: 8,
      guardrail_count: guardrail,
      outcome: OUTCOMES[Math.abs((s >> 24) % OUTCOMES.length)],
      persona: PERSONAS[Math.abs((s >> 28) % PERSONAS.length)],
      duration_seconds: rnd(120, 900),
      summary_text: pick([
        "Mijoz kredit karta haqida so'radi. Operator taklif qildi.",
        "Depozit shartlari muhokama qilindi. Mijoz qiziqdi.",
        "Kredit so'rovi. KYC to'liq bajarildi.",
        "Savol-javob. Mijoz rad etdi.",
        "Operator guardrail kalit so'zlardan foydalandi.",
      ]),
      created_at: ts.toISOString(),
    });
  }
  return calls;
}

exports.handler = async (event) => {
  const params = event.queryStringParameters || {};
  const limit  = Math.min(parseInt(params.limit  || '50'),  200);
  const offset = parseInt(params.offset || '0');

  const calls = makeCalls(42, limit, offset);

  return {
    statusCode: 200,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
    },
    body: JSON.stringify(calls),
  };
};
