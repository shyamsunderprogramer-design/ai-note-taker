// Optional plaintext copy, private to this app profile and outside the source tree.
const path = require('node:path');
const {readPrivateFile, writePrivateFile} = require('./auth-session');
const PROVIDER_ENV_MAP = Object.freeze({openai:'OPENAI_API_KEY', anthropic:'ANTHROPIC_API_KEY', google:'GOOGLE_API_KEY',
  xai:'XAI_API_KEY', deepseek:'DEEPSEEK_API_KEY', groq:'GROQ_API_KEY', 'ollama-cloud':'OLLAMA_CLOUD_API_KEY', perplexity:'PERPLEXITY_API_KEY'});
const envPath = directory => path.join(directory, 'providers', '.env');
function updateProviderEnv(directory, key, value) {
  if (!Object.values(PROVIDER_ENV_MAP).includes(key)) throw Error('Unsupported provider setting.');
  if (value !== null && (typeof value !== 'string' || !/^[\x21-\x7e]{10,4096}$/.test(value))) throw Error('Invalid provider key.');
  const filename = envPath(directory);
  let content = '';
  try { content = readPrivateFile(filename).toString('utf8'); }
  catch (error) { if (error.code !== 'ENOENT') throw Error('Unable to read the local provider .env file.'); if (value === null) return null; }
  const pattern = new RegExp(`^\\s*(?:export\\s+)?${key}\\s*=`);
  const lines = content.split(/\r?\n/).filter(line => !pattern.test(line));
  if (value !== null) lines.push(`${key}=${JSON.stringify(value)}`);
  const next = lines.filter((line, index) => line || index < lines.length - 1).join('\n') + '\n';
  if (Buffer.byteLength(next) > 128 * 1024) throw Error('Local provider .env file is too large.');
  writePrivateFile(filename, next);
  return value === null ? null : filename;
}
module.exports = {PROVIDER_ENV_MAP, envPath, updateProviderEnv};
