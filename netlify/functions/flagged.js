// netlify/functions/flagged.js
// Returns calls that failed quality or fired guardrails
// API key is NEVER sent to the browser

const BRANCHES = [
  'Yunusobod filiali', 'Chilonzor filiali', 'Mirzo Ulugbek filiali',
  'Sergeli filiali', 'Olmazor filiali', 'Shayxontohur filiali',
];
const OUTCOMES  = ['escalated', 'rejected', 'interested'];
const PERSONAS  = ['formal', 'casual', 'analytical', 'emotional'];
const SUMMARIES = [
  "Mijoz shikoyat qildi. Operator guardrail so'zidan foydalandi.",
  "KYC to'liq emas, kredit so'rovi rad etildi.",
  "Operator belgilangan iboralardan foydalandi. Eskalyatsiya.",
  "Sifat past. Mijoz qo'ng'iroqni tugatdi.",
  "Guardrail ogohlantirish. Muqobil ibora taklif qilindi.",
];

function pick(arr) { return arr[Math.floor(Math.random() * arr.length)]; }

function makeFlagged(seed = 7) {
  let s = seed;
  const calls = [];
  for (let i = 0; i < 30; i++) {
    s = (s * 1664525 + 1013904223) & 0xffffffff;
    const quality       = 20 + Math.abs(s % 40);   // 20–59 (always flagged range)
    const guardrail     = 1  + Math.abs((s >> 8) % 4);
    const kyc_done      = Math.abs((s >> 4) % 6);
    const ts = new Date(Date.now() - Math.abs((s >> 12) % (14 * 86400 * 1000)));
    calls.push({
      id:              `call-${(s >>> 0).toString(16).padStart(8, '0')}-f${i}`,
      branch_name:     BRANCHES[Math.abs((s >> 16) % BRANCHES.length)],
      operator_id:     `op-${Math.abs((s >> 20) % 8) + 1}`,
      quality_score:   quality,
      kyc_done,
      kyc_total:       8,
      guardrail_count: guardrail,
      outcome:         OUTCOMES[Math.abs((s >> 24) % OUTCOMES.length)],
      persona:         PERSONAS[Math.abs((s >> 28) % PERSONAS.length)],
      duration_seconds: 60 + Math.abs(s % 300),
      summary_text:    pick(SUMMARIES),
      created_at:      ts.toISOString(),
    });
  }
  return calls;
}

exports.handler = async () => {
  return {
    statusCode: 200,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
    },
    body: JSON.stringify(makeFlagged()),
  };
};
