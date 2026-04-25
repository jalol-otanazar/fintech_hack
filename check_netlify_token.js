const os = require('os');
const path = require('path');
const fs = require('fs');

const locations = [
  path.join(os.homedir(), 'AppData', 'Roaming', 'netlify', 'config.json'),
  path.join(os.homedir(), 'AppData', 'Local', 'netlify', 'config.json'),
  path.join(os.homedir(), '.netlify', 'config.json'),
  path.join(os.homedir(), '.config', 'netlify', 'config.json'),
];

for (const p of locations) {
  if (fs.existsSync(p)) {
    console.log('FOUND:', p);
    console.log(fs.readFileSync(p, 'utf8'));
    process.exit(0);
  }
}
console.log('NOT_FOUND in any location');
