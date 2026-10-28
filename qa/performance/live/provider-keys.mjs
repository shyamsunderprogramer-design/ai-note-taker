// Read existing credentials in memory; never print or persist their values.
import fs from 'node:fs';
import { createRequire } from 'node:module';
import { chromium } from '@playwright/test';
const require = createRequire(import.meta.url);
const { validateProviderKey } = require('../../../electron/lib/provider-key-validation');
const dotenv = require('dotenv');
const vars = { openai: 'OPENAI_API_KEY', anthropic: 'ANTHROPIC_API_KEY', google: 'GOOGLE_API_KEY', xai: 'XAI_API_KEY', deepseek: 'DEEPSEEK_API_KEY', groq: 'GROQ_API_KEY', 'ollama-cloud': 'OLLAMA_CLOUD_API_KEY', perplexity: 'PERPLEXITY_API_KEY' };
const env = { ...process.env };
for (const path of ['backend/.env', '.env']) {
  if (!fs.existsSync(path)) continue;
  for (const [name, value] of Object.entries(dotenv.parse(fs.readFileSync(path)))) if (!env[name]) env[name] = value;
}
let browser, page;
try {
  browser = await chromium.connectOverCDP('http://127.0.0.1:9223', { timeout: 3000 });
  for (const candidate of browser.contexts().flatMap(c => c.pages())) {
    if (await candidate.evaluate(() => typeof window.api?.getApiKey === 'function')) { page = candidate; break; }
  }
} catch { console.log('Desktop key bridge unavailable; checking configured environment keys.'); }
const results = [];
try {
  for (const [provider, variable] of Object.entries(vars)) {
    let key;
    if (page) key = await page.evaluate(async p => (await window.api.getApiKey(p))?.apiKey, provider);
    let source = key ? 'encrypted storage' : 'environment';
    key ||= env[variable] || (provider === 'google' ? env.GEMINI_API_KEY : '') || (provider === 'ollama-cloud' ? env.OLLAMA_API_KEY : '');
    if (!key) { results.push({ provider, status: 'not configured in accessible sources' }); continue; }
    const result = await validateProviderKey(provider, key.trim());
    const record = { provider, source, status: result.success ? 'valid: received answer' : 'failed', ...(result.error ? { error: result.error } : {}) };
    results.push(record);
    console.log(JSON.stringify(record));
  }
} finally { if (browser) await browser.close(); }
fs.writeFileSync('/tmp/ant-provider-key-results.json', JSON.stringify(results, null, 2));
console.log('Results saved without credentials: /tmp/ant-provider-key-results.json');
