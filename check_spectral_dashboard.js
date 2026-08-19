const fs = require("fs");
const path = require("path");

const html = fs.readFileSync(path.join(__dirname, "..", "web", "index.html"), "utf8");
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((match) => match[1]);

if (scripts.length !== 1) throw new Error(`Expected one inline dashboard script, found ${scripts.length}`);
new Function(scripts[0]);

for (const marker of ["Spectral Observatory", "Prévisualiser", "/api/observability", "/api/logs"]) {
  if (!html.includes(marker)) throw new Error(`Missing dashboard observability integration: ${marker}`);
}
for (const forbidden of ["START BOT", "btnStart", "btnStop", "/api/bot/start", "/api/bot/stop", "/api/paper/order"]) {
  if (html.includes(forbidden)) throw new Error(`Forbidden browser execution marker: ${forbidden}`);
}
console.log("check_spectral_dashboard: PASS");
