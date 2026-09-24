// Built renderer -> production routes -> configured Groq (or --local Qwen).
import { chromium } from '@playwright/test';
import { writeFile } from 'node:fs/promises';
const origin = 'http://127.0.0.1:8041';
const local = process.argv.includes('--local');
const selectedModel = local ? 'qwen3.5:9b' : 'groq-gpt-oss-120b';
const browser = await chromium.launch({headless:true});
try {
  const page = await browser.newPage({serviceWorkers:'block'});
  await page.route('**/*', route => {
    const url = new URL(route.request().url());
    if (url.origin === origin) return route.continue();
    if (url.pathname === '/auth/status') return route.fulfill({json:{auth_required:false}});
    return route.fulfill({status:503, json:{detail:'Isolated QA'}});
  });
  await page.goto(`${origin}/index.html`);
  await page.waitForLoadState('networkidle');
  const resumeMode = process.argv.includes('--resume');
  const results = await page.evaluate(async ({resumeMode, selectedModel, local}) => {
    API_BASE = location.origin;
    await resumeContextReady;
    if (resumeMode) {
      const files = new DataTransfer();
      files.items.add(new File(['Alex Rivera. Software engineer at Acme. Built a Python inventory service. Used PostgreSQL. No other work experience is provided.'], 'sample-resume.md', {type:'text/markdown'}));
      resumeFileInput.files = files.files;
      resumeFileInput.dispatchEvent(new Event('change', {bubbles:true}));
      while (resumeUploadButton.disabled) await new Promise(resolve => setTimeout(resolve, 20));
      if (!resumeAnswerContext) throw new Error('Resume upload failed');
    }
    // getProviders is deliberately absent: exercise the real web fallback.
    window.api = {getStreamUrlWithMode:(q, mode, style, provider) =>
      `${location.origin}/qa/stream?${new URLSearchParams({q,mode:'adaptive',style:'concise',provider})}`};
    if (local) modelSelect.add(new Option('Qwen QA', selectedModel));
    if (![...modelSelect.options].some(option => option.value === selectedModel)) throw new Error('Cloud model absent from built UI');
    suppressAutoSave = true;
    const rows = [];
    for (const selection of (local ? [selectedModel] : [selectedModel, 'auto'])) {
      modelSelect.value = selection;
      responseStyleSelect.value = 'concise';
      temperatureSelect.value = '0';
      const start = performance.now();
      const priorMessages = [...document.querySelectorAll('#chatArea > *')];
      await streamAIResponse(resumeMode ? 'In two sentences, tell me about your experience at Acme and the technology you used.' : 'In one sentence, what is Docker?');
      const visibleText = [...document.querySelectorAll('#chatArea > *')].filter(node => !priorMessages.includes(node)).map(node=>node.innerText).join('\n');
      rows.push({model:selection, elapsedSeconds:(performance.now()-start)/1000, visibleText, processing:isProcessing});
    }
    return rows;
  }, {resumeMode, selectedModel, local});
  for (const result of results) {
    result.passed = (resumeMode ? /\bI\b/.test(result.visibleText) && /Acme/.test(result.visibleText) && /Python/.test(result.visibleText) : /docker/i.test(result.visibleText) && /container/i.test(result.visibleText))
      && (local ? /QWEN3\.5:9B/i : /GPT-OSS.*120B/i).test(result.visibleText)
      && !/Error:|AI response failed|AI response timed out|All providers failed/.test(result.visibleText) && !result.processing;
  }
  const report = {passed:results.every(result=>result.passed), results,
    limits:'Isolated loopback server; actual provider keys stay on backend. Synthetic resume. No user database, microphone or desktop capture.'};
  await writeFile(local ? '/tmp/ant-local-browser.json' : '/tmp/ant-cloud-browser.json', JSON.stringify(report,null,2));
  console.log(JSON.stringify(report,null,2));
  if (!report.passed) process.exitCode = 1;
} finally { await browser.close(); }
