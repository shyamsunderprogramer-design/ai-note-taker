// Isolated real-page check with a synthetic native bridge; never calls a user's account.
const {chromium} = require('playwright');
const AxeBuilder = require(process.env.ANT_AXE_MODULE || '@axe-core/playwright').default;
const fs = require('node:fs/promises');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '../../electron/renderer');
const output = '/tmp/ant-subscription-qa/screenshots';
(async () => {
  await fs.mkdir(output, {recursive: true});
  const browser = await chromium.launch({headless: true, executablePath: process.env.ANT_TEST_CHROMIUM});
  const results = [];
  try {
    for (const colorScheme of ['dark', 'light']) for (const width of [1440, 390, 320]) {
      const context = await browser.newContext({viewport: {width, height: width === 1440 ? 900 : 844}, colorScheme, reducedMotion: 'reduce', serviceWorkers: 'block'});
      await context.route('**/*', async route => {
        const url = new URL(route.request().url());
        if (url.origin === 'http://localhost:38127') {
          const file = path.resolve(root, '.' + decodeURIComponent(url.pathname));
          if (!file.startsWith(root + path.sep)) return route.abort();
          const types = {'.html':'text/html', '.js':'text/javascript', '.css':'text/css', '.woff2':'font/woff2', '.png':'image/png', '.jpg':'image/jpeg'};
          try { return route.fulfill({body: await fs.readFile(file), contentType: types[path.extname(file)] || 'application/octet-stream'}); } catch { return route.fulfill({status:404, body:''}); }
        }
        if (url.pathname === '/auth/status') return route.fulfill({json: {auth_required: false}});
        if (['/health', '/auth/me'].includes(url.pathname)) return route.fulfill({json: {status:'ok', id:'test', username:'Test'}});
        return route.fulfill({status:503, json:{detail:'Isolated UI test'}});
      });
      await context.addInitScript(() => {
        const storage = new Map([['hasOnboarded', true]]);
        localStorage.setItem('hasOnboarded', 'true');
        let state = {accounts:[], active:'', enabled:false, connected:false, models:[], fallback:'', paused:false, welcomeSeen:false, locals:['local:small'], primary:'chatgpt', crossFallback:false,
          ollama:{running:true,connected:true,enabled:false,name:'Ollama tester',model:'',models:[{slug:'first:cloud',name:'First cloud model'},{slug:'second:cloud',name:'Second cloud model'}]}};
        let listener, rejectLogin;
        window.testBridge = {savedKeys: [], events: [], mode: 'success', state: () => state, listeners: () => !!listener};
        const result = value => ({value});
        window.api = {
          storeGet: async key => storage.get(key), storeSet: async (key, value) => {storage.set(key, value);},
          hasApiKey: async () => ({hasKey:false}),
          saveApiKey: async (provider, key, syncToEnv) => {window.testBridge.savedKeys.push({provider,syncToEnv});return {success:true,envPath:syncToEnv?'/private/test-profile/providers/.env':null};},
          subscriptions: {
            status: async () => result({...state}), refresh: async () => result({...state}),
            connect: async () => {
              if (window.testBridge.mode === 'pending') return new Promise((_resolve, reject) => {rejectLogin = reject;});
              state = {...state, accounts:[{id:'one', label:'long.account.name@example.com · Account 1',connected:true}], active:'one', enabled:true, connected:true, models:[{slug:'model-one', name:'Available subscription model'}]};
              return result({...state});
            },
            cancelLogin: async () => { rejectLogin?.(Error('Sign-in cancelled.')); return result(state); },
            disconnect: async () => {state={...state, connected:false, enabled:false, models:[]};return result(state);},
            connectOllama: async () => {state={...state,ollama:{...state.ollama,enabled:true}};return result(state);},
            disconnectOllama: async () => {state={...state,ollama:{...state.ollama,enabled:false}};return result(state);},
            cancelOllama: async () => result(state),
            addOllamaModel: async name => {state={...state,ollama:{...state.ollama,models:[...state.ollama.models,{slug:name,name}]}};return result(state);},
            ollamaUsage: async () => result(true), ollamaDownload: async () => result(true),
            settings: async change => {state={...state,...change}; if(change.ollamaModel) state={...state,ollama:{...state.ollama,model:change.ollamaModel}}; if(change.retry) state.paused=false; return result(state);},
            usage: async () => result(true), cancel: async () => result(true),
            onEvent: cb => {listener=cb;return () => {listener=null;};},
            start: async (id, body) => {
              window.testBridge.events.push(body);
              setTimeout(() => {
                const events=[{type:'meta',display:'ChatGPT plan'},{type:'chunk',content:'Partial'},
                  {type:'notice',message:'ChatGPT limit reached (429) → switched to local:small on this device.'},
                  {type:'reset'},{type:'meta',display:'local:small · Local fallback'},{type:'chunk',content:'Replacement answer'},{type:'done'},{type:'end'}];
                for(const e of events) listener?.(id,e);
              },30);
              return result(true);
            },
          },
        };
      });
      const page = await context.newPage(), errors=[];
      page.on('pageerror', error => {errors.push(error.message); console.error('Page error:', error.message);});
      await page.goto('http://localhost:38127/index.html');
      await page.waitForLoadState('networkidle');
      if (await page.locator('#onboardSkipBtn').isVisible()) await page.locator('#onboardSkipBtn').click();
      await page.locator('#subscriptionShortcut').focus();
      await page.keyboard.press('Enter');
      await page.locator('#providersTitle').waitFor();
      assert.equal(await page.locator('[data-tab="subscriptions"]').count(),0);
      // A browser can scroll a drag region programmatically while Electron swallows
      // physical gestures. Verify both the native hit region and wheel behavior.
      const settingsBody = page.locator('#settingsPanel .settings-body');
      assert.equal(await page.locator('#settingsPanel').evaluate(n=>getComputedStyle(n).webkitAppRegion),'no-drag');
      assert.equal(await settingsBody.evaluate(n=>getComputedStyle(n).webkitAppRegion),'no-drag');
      const bodyBox = await settingsBody.boundingBox();
      await page.mouse.move(bodyBox.x + bodyBox.width / 2, bodyBox.y + 80);
      await page.mouse.wheel(0, 500);
      await page.waitForFunction(() => document.querySelector('#settingsPanel .settings-body').scrollTop > 100);
      await page.mouse.wheel(0, -1000);
      await page.waitForFunction(() => document.querySelector('#settingsPanel .settings-body').scrollTop === 0);
      await page.screenshot({path:`${output}/${colorScheme}-${width}-disconnected.png`});
      await page.locator('#chatgptConnection > summary').click();
      assert.match(await page.locator('#subscriptionStatus').innerText(), /No ChatGPT/);
      await page.locator('#subscriptionConnect').click();
      await page.locator('#subscriptionWelcome').waitFor({state:'visible'});
      assert.equal(await page.locator('#modelSelect').inputValue(), 'subscription');
      const welcomeAxe = await new AxeBuilder({page}).include('#subscriptionWelcome').withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze();
      assert.deepEqual(welcomeAxe.violations.map(v=>v.id), []);
      await page.screenshot({path:`${output}/${colorScheme}-${width}-welcome.png`});
      await page.keyboard.press('Escape');
      assert.equal(await page.locator('#subscriptionWelcome').isVisible(), false);
      await page.locator('#subscriptionFallback').selectOption('local:small');
      await page.locator('#subscriptionUse').click();
      await page.waitForFunction(() => document.getElementById('modelSelect').value === 'subscription');
      assert.equal(await page.evaluate(() => testBridge.state().fallback), 'local:small');
      assert.equal(await page.locator('#subscriptionCrossFallback').isChecked(),false);
      await page.locator('#ollamaConnection > summary').click();
      await page.locator('#ollamaAccountConnect').click();
      await page.waitForFunction(() => !document.getElementById('ollamaAccountModel').disabled);
      await page.locator('#ollamaAccountModel').selectOption('second:cloud');
      await page.waitForFunction(() => testBridge.state().ollama.model === 'second:cloud');
      await page.locator('#ollamaAccountUse').click();
      await page.waitForFunction(() => testBridge.state().primary === 'ollama-cloud');
      assert.equal(await page.locator('#modelSelect').inputValue(),'subscription');
      assert.match(await page.locator('#modelProviderStatus').innerText(),/Ollama/);
      await page.locator('#subscriptionCrossFallback').check();
      await page.waitForFunction(() => testBridge.state().crossFallback);
      await page.locator('#ollamaAccountTitle').scrollIntoViewIfNeeded();
      // Allow the translucent shell's compositor to repaint after scrolling upward.
      await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
      await page.screenshot({path:`${output}/${colorScheme}-${width}-ollama.png`});
      await page.locator('#ollamaAccountTitle').locator('..').locator('summary').click();
      await page.locator('#ollamaAccountModelName').fill('added:cloud');
      await page.locator('#ollamaAccountAdd').click();
      await page.waitForFunction(() => document.querySelector('#ollamaAccountModel option[value="added:cloud"]'));
      await page.locator('#ollamaAccountTitle').locator('..').locator('summary').click();
      await page.locator('#subscriptionPrimary').selectOption('chatgpt');
      await page.locator('#subscriptionSettings').evaluate(node => node.closest('.settings-body').scrollTop=0);
      await page.screenshot({path:`${output}/${colorScheme}-${width}-connected.png`});
      const scan = await new AxeBuilder({page}).include('#providersSettings').withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze();
      assert.deepEqual(scan.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>n.target)})), []);
      const overflow = await page.locator('#providersSettings').evaluate(node => node.scrollWidth > node.clientWidth + 1);
      assert.equal(overflow, false);
      // Exercise the real chat integration, including replacing partially streamed output.
      await page.evaluate(async () => {
        suppressAutoSave = true;
        await streamRecoveringAnswer('Test the subscription bridge');
      });
      assert.match(await page.locator('#subscriptionNoticeText').innerText(), /429.*switched/);
      assert.equal(await page.evaluate(() => testBridge.listeners()), false);
      assert.equal(await page.evaluate(() => testBridge.events.length), 1);
      assert.ok(await page.getByText('Replacement answer', {exact:true}).count());
      assert.equal(await page.getByText('PartialReplacement answer', {exact:true}).count(), 0);
      await page.locator('#ollamaAccountDisconnect').click();
      await page.waitForFunction(() => !testBridge.state().ollama.enabled);
      assert.equal(await page.evaluate(() => testBridge.state().enabled),true);
      for (const provider of ['anthropic','google','xai','groq']) {
        await page.locator(`#cfg-${provider}`).click();
        assert.equal(await page.evaluate(() => activeProvider),provider);
        assert.equal(await page.locator('#providerConfigPanel').evaluate(n=>n.classList.contains('open')),true);
        assert.equal(await page.locator('#configSyncEnvCheckbox').isChecked(),true);
        if (provider === 'groq') {
          await page.locator('#configApiKeyInput').fill('synthetic-testing-key');
          await page.locator('#configSaveBtn').click();
          await page.waitForFunction(() => document.getElementById('configTestResult').textContent.includes('providers/.env'));
          assert.equal(await page.locator('#configApiKeyInput').inputValue(),'');
          await page.locator('#configSyncEnvCheckbox').uncheck();
          await page.locator('#configApiKeyInput').fill('synthetic-testing-key');
          await page.locator('#configSaveBtn').click();
          await page.waitForFunction(() => document.getElementById('configTestResult').textContent.includes('encrypted storage'));
          assert.deepEqual(await page.evaluate(() => testBridge.savedKeys),[{provider:'groq',syncToEnv:true},{provider:'groq',syncToEnv:false}]);
          const configAxe=await new AxeBuilder({page}).include('#providerConfigPanel').withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze();
          assert.deepEqual(configAxe.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>n.target)})),[]);
          await page.screenshot({path:`${output}/${colorScheme}-${width}-api-key.png`});
          await page.locator('#configApiKeyInput').focus();
          await page.keyboard.press('Escape');
          assert.equal(await page.evaluate(() => document.activeElement.id),'cfg-groq');
        }
        await page.evaluate(() => {closeProviderConfig();document.querySelector('[data-tab="providers"]').click();});
      }
      await page.locator('#subscriptionDisconnect').click();
      await page.evaluate(() => testBridge.mode='pending');
      await page.locator('#subscriptionConnect').click();
      await page.locator('#subscriptionCancel').click();
      await page.waitForFunction(() => document.getElementById('subscriptionFeedback').textContent.includes('cancelled'));
      assert.equal(await page.locator('#subscriptionConnect').isEnabled(), true);
      await page.locator('#subscriptionConnect').focus();
      await page.keyboard.press('Escape');
      assert.equal(await page.evaluate(() => document.activeElement.id), 'subscriptionShortcut');
      assert.equal(await page.locator('#settingsPanel').evaluate(n=>n.classList.contains('open')), false);
      assert.deepEqual(errors, []);
      results.push({width,colorScheme,axe:scan.violations.length,welcomeAxe:welcomeAxe.violations.length,errors});
      await context.close();
    }
    await fs.writeFile(`${output}/results.json`,JSON.stringify(results,null,2));
    console.log(JSON.stringify(results,null,2));
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
