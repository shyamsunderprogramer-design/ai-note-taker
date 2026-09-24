// Production HTML/script smoke check with synthetic API responses; no user backend calls.
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { dirname, resolve, extname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from '@playwright/test';

const dist = resolve(dirname(fileURLToPath(import.meta.url)), '../../../apps/web/dist');
const types = { '.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css', '.json': 'application/json', '.png': 'image/png', '.svg': 'image/svg+xml', '.woff2': 'font/woff2' };
const server = createServer(async (req, res) => {
  const path = resolve(dist, '.' + new URL(req.url, 'http://localhost').pathname);
  if (!path.startsWith(dist + '/')) { res.writeHead(404).end(); return; }
  try { res.setHeader('Content-Type', types[extname(path)] || 'application/octet-stream'); res.end(await readFile(path)); }
  catch { res.writeHead(404).end(); }
});
await new Promise((done, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', done); });
let browser;
try {
  browser = await chromium.launch({ headless: true, args: ['--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream'] });
  const origin = `http://127.0.0.1:${server.address().port}`;
  const context = await browser.newContext({ serviceWorkers: 'block' });
  await context.route('**/*', async route => {
    const url = new URL(route.request().url());
    if (url.origin === origin) return route.continue();
    if (url.pathname === '/auth/status') return route.fulfill({ json: { auth_required: false } });
    return route.fulfill({ status: 503, json: { detail: 'Backend unavailable during isolated UI smoke test' } });
  });
  const results = [];
  for (const name of ['signin.html', 'index.html', 'job-tracker.html', 'study-plan.html', 'resume-review-v2.html']) {
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.stack || error.message));
    const response = await page.goto(`${origin}/${name}`);
    await page.waitForLoadState('networkidle');
    if (name === 'index.html') {
      const preview = await page.evaluate(() => {
        textInput.value = 'My typed question';
        const speech = 'This is a complete spoken sentence that should remain readable without losing the beginning or cutting words.';
        showPartialTranscript(speech);
        const result = textInput.value === 'My typed question'
          && !textInput.classList.contains('partial-transcript')
          && document.getElementById('transcriptStripContent').textContent === speech;
        textInput.value = '';
        return result;
      });
      if (!preview) errors.push('Speech preview overwrote the input or cut words');
      const resume = await page.evaluate(async () => {
        const originalFetch = window.fetch;
        try {
          window.fetch = async () => new Response(JSON.stringify({text:'Alex built a Python inventory system at Acme.'}), {status:200});
          const files = new DataTransfer();
          files.items.add(new File(['Alex built a Python inventory system at Acme.'], 'resume.md', {type:'text/markdown'}));
          resumeFileInput.files = files.files;
          resumeFileInput.dispatchEvent(new Event('change', {bubbles:true}));
          while (resumeUploadButton.disabled) await new Promise(resolve => setTimeout(resolve, 10));
          const prompt = buildInterviewPrompt('Tell me about your experience');
          const loaded = !resumeStatus.hidden && resumeName.textContent.includes('resume.md') && prompt.includes('Acme') && /first[- ]person/.test(prompt);
          const once = buildInterviewPrompt(prompt) === prompt;
          resumeRemove.click();
          while (resumeRemove.disabled) await new Promise(resolve => setTimeout(resolve, 10));
          const removed = resumeStatus.hidden && !buildInterviewPrompt('Question').includes('Acme');
          window.fetch = async () => new Response(JSON.stringify({detail:'No readable resume text found.'}), {status:422});
          const rejectedFile = new DataTransfer();
          rejectedFile.items.add(new File(['unreadable file'], 'rejected.pdf', {type:'application/pdf'}));
          resumeFileInput.files = rejectedFile.files;
          resumeFileInput.dispatchEvent(new Event('change', {bubbles:true}));
          while (resumeUploadButton.disabled) await new Promise(resolve => setTimeout(resolve, 10));
          const failureVisible = !resumeStatus.hidden && !resumeRemove.disabled && resumeName.textContent.includes('No readable resume text found');
          resumeRemove.click();
          while (resumeRemove.disabled) await new Promise(resolve => setTimeout(resolve, 10));
          return {loaded, once, removed, failureVisible};
        } finally { window.fetch = originalFetch; }
      });
      if (!resume.loaded || !resume.once || !resume.removed || !resume.failureVisible) errors.push(`Resume context regression: ${JSON.stringify(resume)}`);
      await page.evaluate(async () => {
        await appSettings.set(RESUME_CONTEXT_KEY, {name:'persistent-resume.md',text:'Alex built a Python inventory service at Acme.'});
      });
      await page.reload();
      await page.waitForLoadState('networkidle');
      if (await page.locator('#onboardSkipBtn').isVisible()) await page.locator('#onboardSkipBtn').click();
      if (!await page.locator('#answerContextPopover').isVisible()) await page.locator('#answerContextButton').click();
      await page.locator('#jobDescriptionButton').click();
      await page.locator('#jobDescriptionInput').fill('Platform engineer: Python, Kubernetes, and AWS certification required.');
      await page.locator('#jobDescriptionInput').press('Enter');
      if (!await page.locator('#jobDescriptionDialog').isVisible()) errors.push('JD editor Enter triggered a chat shortcut');
      await page.locator('#jobDescriptionSave').click();
      await page.waitForFunction(() => !document.getElementById('jobDescriptionDialog').open);
      const combined = await page.evaluate(() => {
        const prompt = buildInterviewPrompt('Why am I a fit?');
        return prompt.includes('Acme') && prompt.includes('Kubernetes') && prompt.includes("not the candidate's qualifications")
          && buildInterviewPrompt(prompt) === prompt
          && !document.querySelector('.input-pill #resumeContextUpload')
          && !document.querySelector('.input-pill #jobDescriptionButton');
      });
      if (!combined) errors.push('Combined resume/JD context or separate layout failed');
      await page.reload();
      await page.waitForLoadState('networkidle');
      if (!await page.locator('#answerContextPopover').isVisible()) await page.locator('#answerContextButton').click();
      await page.locator('#jobDescriptionButton').click();
      if (!(await page.locator('#jobDescriptionInput').inputValue()).includes('Kubernetes')) errors.push('JD did not persist');
      await page.locator('#jobDescriptionInput').fill('Unsaved change');
      await page.locator('#jobDescriptionCancel').click();
      if (!await page.evaluate(() => buildInterviewPrompt('Question').includes('Kubernetes'))) errors.push('Cancel changed active JD');
      if (!await page.locator('#answerContextPopover').isVisible()) await page.locator('#answerContextButton').click();
      await page.locator('#jobDescriptionButton').click();
      await page.locator('#jobDescriptionRemove').click();
      await page.waitForFunction(() => !document.getElementById('jobDescriptionDialog').open);
      await page.reload();
      await page.waitForLoadState('networkidle');
      if (!await page.evaluate(async () => { await jobDescriptionReady; return !jobDescriptionContext && !buildInterviewPrompt('Question').includes('Kubernetes'); })) errors.push('JD removal did not persist');
      const compactContext = await page.evaluate(() => {
        const panel = document.getElementById('answerContextPopover');
        return !panel.matches(':popover-open') && panel.getBoundingClientRect().height === 0
          && !!document.querySelector('.compact-header #answerContextButton');
      });
      if (!compactContext) errors.push('Context controls consume space outside the artwork header');
      await page.screenshot({path: '/tmp/ant-context-compact.png'});
      const persisted = await page.evaluate(async () => {
        await resumeContextReady;
        const restored = !resumeStatus.hidden && resumeName.textContent.includes('persistent-resume.md') && buildInterviewPrompt('Describe my work').includes('Acme');
        resumeRemove.click();
        while (resumeRemove.disabled) await new Promise(resolve => setTimeout(resolve, 10));
        return restored && (await appSettings.get(RESUME_CONTEXT_KEY)) === null;
      });
      await page.reload();
      await page.waitForLoadState('networkidle');
      const removedAfterReload = await page.evaluate(async () => { await resumeContextReady; return resumeAnswerContext === null && resumeStatus.hidden; });
      if (!persisted || !removedAfterReload) errors.push('Resume persistence or permanent removal failed');
      const scrolling = await page.evaluate(async () => {
        const frame = () => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
        const oldStyle = chatArea.style.cssText;
        const oldSave = suppressAutoSave;
        suppressAutoSave = true;
        chatArea.style.cssText = 'height:180px;max-height:180px;flex:none;overflow-y:auto';
        const filler = document.createElement('div');
        filler.style.height = '1200px';
        filler.style.flexShrink = '0';
        chatArea.appendChild(filler);
        streamMessage('assistant', '');
        scrollChat(false, true);
        await frame();
        batchUpdateBubble('Hello');
        batchUpdateBubble('Hello reader');
        await frame();
        const notDuplicated = latestBotMessage.bubble.dataset.fullText === 'Hello reader';
        const follows = chatArea.scrollHeight - chatArea.scrollTop - chatArea.clientHeight < 5;
        chatArea.dispatchEvent(new WheelEvent('wheel', {deltaY: -100, bubbles: true}));
        chatArea.scrollTop = 100;
        chatArea.dispatchEvent(new Event('scroll'));
        await frame();
        const position = chatArea.scrollTop;
        batchUpdateBubble('Hello reader. New answer text. '.repeat(30));
        await frame();
        const stayed = Math.abs(chatArea.scrollTop - position) < 2;
        finalizeBubble(latestBotMessage.bubble, formatMessage('Complete answer. '.repeat(60)));
        await frame();
        const finalStayed = Math.abs(chatArea.scrollTop - position) < 2;
        scrollChat(false, true);
        await frame();
        const resumed = chatArea.scrollHeight - chatArea.scrollTop - chatArea.clientHeight < 5;
        latestBotMessage = null;
        filler.remove();
        chatArea.style.cssText = oldStyle;
        suppressAutoSave = oldSave;
        return {notDuplicated, follows, stayed, finalStayed, resumed};
      });
      if (Object.values(scrolling).some(value => !value)) errors.push(`Streaming scroll regression: ${JSON.stringify(scrolling)}`);
      const captured = await page.evaluate(async () => {
        const originalSubmit = submitAudio;
        const originalStreaming = startStreamingTranscription;
        const originalReady = isBackendReady;
        const blobs = [];
        try {
          isBackendReady = true;
          startStreamingTranscription = () => {};
          submitAudio = async blob => { blobs.push(blob.size); setProcessingUI(false); };
          for (let cycle = 0; cycle < 2; cycle++) {
            textInput.value = '';
            textInput.focus();
            textInput.dispatchEvent(new KeyboardEvent('keydown', {key:'Enter',bubbles:true,cancelable:true}));
            const deadline = Date.now() + 5000;
            while ((!mediaRecorder || mediaRecorder.state !== 'recording') && Date.now() < deadline) {
              await new Promise(resolve => setTimeout(resolve, 50));
            }
            if (!mediaRecorder || mediaRecorder.state !== 'recording') throw new Error('Recorder did not start');
            await new Promise(resolve => setTimeout(resolve, 600));
            showPartialTranscript('Live partial transcript');
            if (cycle === 0) textInput.dispatchEvent(new KeyboardEvent('keydown', {key:'Enter',bubbles:true,cancelable:true}));
            else listenBtn.click();
            const stopDeadline = Date.now() + 3000;
            while (blobs.length <= cycle && Date.now() < stopDeadline) await new Promise(resolve => setTimeout(resolve, 50));
            if (isListening || blobs.length !== cycle + 1) throw new Error('Recorder did not stop and submit exactly once');
          }
          return blobs;
        } finally {
          submitAudio = originalSubmit;
          startStreamingTranscription = originalStreaming;
          isBackendReady = originalReady;
          textInput.value = '';
        }
      });
      if (captured.length !== 2 || captured.some(size => size < 256)) errors.push(`Recording cycles failed: ${JSON.stringify(captured)}`);
      const recording = await page.evaluate(async () => {
        const originalFetch = window.fetch;
        const originalStream = streamAIResponse;
        const originalSpeakers = speakerDiarizationEnabled;
        const originalScreenshot = pendingOcrScreenshot;
        const calls = [];
        const answers = [];
        try {
          speakerDiarizationEnabled = false;
          pendingOcrScreenshot = null;
          textInput.value = 'incomplete provisional transcript';
          window.fetch = async (url, options) => {
            calls.push({ url: String(url), hasAudio: options.body instanceof FormData });
            return new Response(JSON.stringify({text:'The complete recorded question.'}), {status:200,headers:{'Content-Type':'application/json'}});
          };
          streamAIResponse = async text => { answers.push(text); setProcessingUI(false); };
          await submitAudio(new Blob(['synthetic recording'], {type:'audio/webm'}));
          return {calls, answers};
        } finally {
          window.fetch = originalFetch;
          streamAIResponse = originalStream;
          speakerDiarizationEnabled = originalSpeakers;
          pendingOcrScreenshot = originalScreenshot;
          textInput.value = '';
        }
      });
      if (recording.calls.length !== 1 || !recording.calls[0].hasAudio || recording.answers.join('') !== 'The complete recorded question.') {
        errors.push(`Complete-recording regression: ${JSON.stringify(recording)}`);
      }
      const keyboard = await page.evaluate(() => {
        let starts = 0;
        const originalClick = listenBtn.click;
        listenBtn.click = () => { starts++; setListeningUI(true); };
        setListeningUI(false);
        textInput.value = '';
        textInput.focus();
        textInput.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true, cancelable: true }));
        const started = isListening;
        textInput.value = 'Provisional speech must not be submitted as typed text';
        textInput.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true, cancelable: true }));
        const stopped = !isListening;
        const originalSubmitText = submitText;
        let unintendedSubmissions = 0;
        submitText = async () => { unintendedSubmissions++; };
        listenBtn.click = originalClick;
        setListeningUI(true);
        listenBtn.click();
        const buttonStopped = !isListening;
        submitText = originalSubmitText;
        listenBtn.click = () => { starts++; setListeningUI(true); };
        textInput.value = '';
        textInput.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', repeat: true, bubbles: true, cancelable: true }));
        textInput.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', shiftKey: true, bubbles: true, cancelable: true }));
        const control = document.createElement('input');
        document.body.appendChild(control);
        control.focus();
        control.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true, cancelable: true }));
        control.remove();
        setListeningUI(true);
        setProcessingUI(true);
        setProcessingUI(false);
        const restored = isListening && !listenBtn.disabled && listenLabel.textContent === 'Stop';
        listenBtn.click = originalClick;
        setListeningUI(false);
        return { starts, started, stopped, restored, buttonStopped, unintendedSubmissions };
      });
      if (keyboard.starts !== 1 || !keyboard.started || !keyboard.stopped || !keyboard.restored || !keyboard.buttonStopped || keyboard.unintendedSubmissions) {
        errors.push(`Enter/processing regression: ${JSON.stringify(keyboard)}`);
      }
      const live = await page.evaluate(() => {
        const before = currentMessages.length;
        showLiveHint({ session_id: 'first-call', answer_id: 1, partial: true, text: 'Opening sentence.' });
        showLiveHint({ session_id: 'first-call', answer_id: 1, partial: false, text: 'Complete first answer.' });
        showLiveHint({ session_id: 'reconnected-call', answer_id: 1, partial: false, text: 'Independent second answer.' });
        const saved = currentMessages.slice(before).map(message => message.text);
        return {
          saved,
          visible: ['Complete first answer.', 'Independent second answer.'].every(text =>
            [...document.querySelectorAll('.msg-bubble')].some(bubble => bubble.textContent.includes(text))),
        };
      });
      if (!live.visible || JSON.stringify(live.saved) !== JSON.stringify(['Complete first answer.', 'Independent second answer.'])) {
        errors.push(`Live answer update/reconnect failed: ${JSON.stringify(live)}`);
      }
    }
    results.push({ page: name, status: response.status(), title: await page.title(), errors });
    await page.close();
  }
  console.log(JSON.stringify(results, null, 2));
  if (results.some(result => result.status !== 200 || result.errors.length)) process.exitCode = 1;
} finally {
  await browser?.close();
  await new Promise(done => server.close(done));
}
