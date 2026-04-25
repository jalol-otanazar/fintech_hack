// netlify/functions/operators-stats.js
// Demo operator statistics — API key never exposed

const OPERATORS = [
  { name: 'Aziz Karimov',    branch_name: 'Yunusobod filiali',       total_calls: 87,  avg_quality: 82.4, total_guardrails: 1,  offers_accepted: 34 },
  { name: 'Dilnoza Yusupova',branch_name: 'Chilonzor filiali',       total_calls: 74,  avg_quality: 78.1, total_guardrails: 2,  offers_accepted: 28 },
  { name: 'Jasur Toshmatov', branch_name: 'Mirzo Ulugbek filiali',   total_calls: 91,  avg_quality: 75.6, total_guardrails: 3,  offers_accepted: 31 },
  { name: 'Nodira Rahimova', branch_name: 'Sergeli filiali',         total_calls: 63,  avg_quality: 71.2, total_guardrails: 5,  offers_accepted: 18 },
  { name: 'Sanjar Ergashev', branch_name: 'Olmazor filiali',         total_calls: 55,  avg_quality: 68.9, total_guardrails: 4,  offers_accepted: 15 },
  { name: 'Mavluda Sobirov', branch_name: 'Shayxontohur filiali',    total_calls: 48,  avg_quality: 65.3, total_guardrails: 7,  offers_accepted: 12 },
  { name: 'Behruz Nazarov',  branch_name: 'Yunusobod filiali',       total_calls: 102, avg_quality: 63.0, total_guardrails: 9,  offers_accepted: 24 },
  { name: 'Zulfiya Alimova', branch_name: 'Chilonzor filiali',       total_calls: 39,  avg_quality: 57.8, total_guardrails: 12, offers_accepted: 7  },
];

exports.handler = async () => {
  return {
    statusCode: 200,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
    },
    body: JSON.stringify(OPERATORS),
  };
};
