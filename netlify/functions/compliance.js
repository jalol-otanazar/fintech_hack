// netlify/functions/compliance.js
// Returns guardrail / compliance events for the journal page
// API key is NEVER sent to the browser

const BLOCKED_PHRASES = [
  "kafolatlayman",       // "I guarantee"
  "foizni oshirmaymiz",  // "we won't raise the rate"
  "bepul",               // "free" (misleading)
  "hech qanday xavf yo'q", // "no risk at all"
  "eng yaxshi kredit",   // "best loan" (superlative claim)
];
const REPLACEMENTS = [
  "Hozirgi shartlar asosida taklif qilamiz",
  "Foiz stavkasi shartnoma asosida belgilanadi",
  "Xizmat narxlari haqida batafsil ma'lumot bera olaman",
  "Har qanday moliyaviy mahsulotda ma'lum darajada xavf mavjud",
  "Siz uchun mos variantni ko'rib chiqamiz",
];
const CALL_PREFIXES = ['call-a1b2c3d4', 'call-e5f6a7b8', 'call-c9d0e1f2',
                       'call-23456789', 'call-abcdef01', 'call-98765432',
                       'call-fedcba98', 'call-01234567'];

function makeEvents(seed = 13) {
  let s = seed;
  const events = [];
  for (let i = 0; i < 20; i++) {
    s = (s * 1664525 + 1013904223) & 0xffffffff;
    const idx = Math.abs(s % BLOCKED_PHRASES.length);
    const ts  = new Date(Date.now() - Math.abs((s >> 8) % (30 * 86400 * 1000)));
    events.push({
      id:          `ev-${(s >>> 0).toString(16).padStart(8,'0')}`,
      call_id:     CALL_PREFIXES[Math.abs((s >> 16) % CALL_PREFIXES.length)],
      blocked:     BLOCKED_PHRASES[idx],
      replacement: REPLACEMENTS[idx],
      fired_at:    ts.toISOString(),
      severity:    idx >= 3 ? 'high' : 'medium',
    });
  }
  return events.sort((a, b) => b.fired_at.localeCompare(a.fired_at));
}

exports.handler = async () => {
  return {
    statusCode: 200,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
    },
    body: JSON.stringify(makeEvents()),
  };
};
