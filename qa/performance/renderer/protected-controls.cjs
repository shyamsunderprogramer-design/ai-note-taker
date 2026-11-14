// Real Electron regression for OS popup leakage. Uses synthetic content, no backend.
const { _electron: electron } = require('@playwright/test')
const assert = require('node:assert/strict')
const fs = require('node:fs/promises')
const path = require('node:path')
const os = require('node:os')
const { pathToFileURL } = require('node:url')
const { execFile } = require('node:child_process')
const { promisify } = require('node:util')

async function main() {
  const root = path.resolve(__dirname, '../../..')
  const output = await fs.mkdtemp(path.join(os.tmpdir(), 'ant-controls-'))
  const html = await fs.readFile(path.join(root, 'electron/renderer/index.html'), 'utf8')
  const controls = ['modeSelect', 'modelSelect'].map(id => html.match(new RegExp(`<select id="${id}"[\\s\\S]*?</select>`))[0]).join('')
  const fixture = path.join(output, 'fixture.html')
  await fs.writeFile(fixture, `<!doctype html><html><head><title>ANT Capture QA</title>
    <meta http-equiv="Content-Security-Policy" content="default-src 'self'; style-src 'self' 'unsafe-inline'">
    <link rel="stylesheet" href="${pathToFileURL(path.join(root, 'electron/renderer/style.css'))}">
    <style>body {margin:0;padding:30px;background:#172033;color:white;overflow:auto}
      select {margin-bottom:18px} #hint {margin-top:15px;animation:pulse .3s infinite alternate} @keyframes pulse{to{opacity:.7}} .spacer {height:900px}
    </style></head><body><main><label for="modeSelect">Mode</label><label for="modelSelect">Model</label>${controls}
    <button id="hint" title="Private model availability details">Help</button>
    <button id="icon" title="Settings"><svg width="20" height="20" aria-hidden="true"></svg></button>
    <div class="spacer"></div><label for="bottom">Bottom setting</label><select id="bottom"><option>First</option><option>Second</option></select>
    </main></body></html>`)
  const mainFile = path.join(output, 'main.cjs')
  await fs.writeFile(mainFile, `const { app, BrowserWindow } = require('electron');
    app.setPath('userData', ${JSON.stringify(path.join(output, 'profile'))});
    app.whenReady().then(async () => {
      const window = new BrowserWindow({x:60,y:60,width:640,height:600,show:false,frame:false,
        webPreferences:{preload:${JSON.stringify(path.join(root, 'electron/preload.js'))},contextIsolation:true,nodeIntegration:false}});
      window.setContentProtection(true);
      await window.loadFile(${JSON.stringify(fixture)}); window.show();
    });`)
  let app
  try {
    app = await electron.launch({ args: [mainFile] })
    const page = await app.firstWindow()
    await page.waitForLoadState('domcontentloaded')
    assert.equal(await page.locator('#modelSelect').evaluate(el => getComputedStyle(el).appearance), 'base-select', 'Model must render its picker inside the protected document')
    assert.equal(await page.locator('#modeSelect').evaluate(el => getComputedStyle(el, '::picker(select)').appearance), 'base-select')
    assert.equal(await page.locator('[title]:not([title=""])').count(), 0, 'No native title tooltips')
    await page.locator('#modelSelect').click()
    assert.equal(await page.locator('#modelSelect').evaluate(el => el.matches(':open')), true)
    await page.screenshot({ path: path.join(output, 'model-picker.png') })
    if (process.argv.includes('--capture')) {
      // An opaque synthetic backdrop limits this OS capture to test content.
      const windowId = await app.evaluate(async ({ BrowserWindow }) => {
        const front = BrowserWindow.getAllWindows()[0]
        const bounds = front.getBounds()
        const backdrop = new BrowserWindow({ x:bounds.x-20, y:bounds.y-20, width:bounds.width+40, height:bounds.height+40, frame:false, show:false, backgroundColor:'#256b45' })
        await backdrop.loadURL('data:text/html,<style>body{margin:0;background:%23256b45;animation:pulse .3s infinite alternate}@keyframes pulse{to{background:%23286c48}}</style><body></body>')
        backdrop.showInactive(); front.moveTop(); front.focus()
        return front.id
      })
      await page.locator('#modelSelect').evaluate(el => { if (!el.matches(':open')) el.showPicker() })
      const screenshot = async name => {
        await page.waitForTimeout(250) // Allow the OS compositor to apply exclusion.
        const file = path.join(output, name + '.png')
        await promisify(execFile)('/usr/sbin/screencapture', ['-x', '-R60,60,640,600', file])
        return app.evaluate(({ nativeImage }, filePath) => {
          const image = nativeImage.createFromPath(filePath), pixels = image.toBitmap()
          let green = 0
          for (let i = 0; i < pixels.length; i += 4) {
            // macOS color management may shift the synthetic backdrop slightly.
            if (Math.abs(pixels[i] - 0x45) < 32 && Math.abs(pixels[i + 1] - 0x6b) < 32 && Math.abs(pixels[i + 2] - 0x25) < 32) green++
          }
          return green / (pixels.length / 4)
        }, file)
      }
      await app.evaluate(({ BrowserWindow }, id) => BrowserWindow.fromId(id).setContentProtection(false), windowId)
      const visible = await screenshot('os-unprotected-picker')
      await app.evaluate(({ BrowserWindow }, id) => BrowserWindow.fromId(id).setContentProtection(true), windowId)
      const hidden = await screenshot('os-protected-picker')
      assert(visible < 0.1, `Control capture must show fixture: ${visible}`)
      assert(hidden > 0.99, `Protected picker must disappear into test backdrop: ${hidden}`)
      if (process.argv.includes('--screen-capture-kit')) {
        const binary = path.join(output, 'capture-fixture')
        await promisify(execFile)('/usr/bin/xcrun', ['swiftc', '-parse-as-library',
          path.join(__dirname, 'capture-fixture.swift'), '-O', '-module-cache-path', path.join(output, 'modules'), '-o', binary])
        const pid = await app.evaluate(() => process.pid)
        const captureKit = async (name, mode) => {
          await page.waitForTimeout(250)
          const target = path.join(output, name + '.png')
          await promisify(execFile)(binary, [String(pid), target, mode])
          const files = mode === 'display-stream'
            ? (await fs.readdir(output)).filter(file => file.startsWith(name + '.png.frame-')).map(file => path.join(output, file))
            : [target]
          assert(files.length > 0, 'Recorder must deliver frames')
          if (mode === 'display-stream') assert(files.length > 1, 'Continuous recording must deliver multiple frames')
          return app.evaluate(({nativeImage}, files) => {
            const frames = files.map(file => {
              const pixels = nativeImage.createFromPath(file).toBitmap()
              let fixturePixels = 0, unexpectedPixels = 0
              for (let i = 0; i < pixels.length; i += 4) {
                const [b,g,r] = [pixels[i],pixels[i+1],pixels[i+2]]
                if (Math.abs(b-0x33)<20 && Math.abs(g-0x20)<20 && Math.abs(r-0x17)<20) fixturePixels++
                const blank = b < 10 && g < 10 && r < 10
                const backdrop = Math.abs(b-0x45)<32 && Math.abs(g-0x6b)<32 && Math.abs(r-0x25)<32
                if (!blank && !backdrop) unexpectedPixels++
              }
              return {fixtureFraction:fixturePixels/(pixels.length/4), unexpectedPixels}
            })
            return {fixtureFraction:Math.max(...frames.map(f=>f.fixtureFraction)),
              maxUnexpectedPixels:Math.max(...frames.map(f=>f.unexpectedPixels)), frames:frames.length}
          }, files)
        }
        const observations = []
        for (const mode of ['window', 'display', 'display-stream']) {
          await app.evaluate(({BrowserWindow}, id) => BrowserWindow.fromId(id).setContentProtection(false), windowId)
          const control = await captureKit('sck-' + mode + '-unprotected-picker', mode)
          assert(control.fixtureFraction > 0.1, `${mode} control must show fixture: ${control.fixtureFraction}`)
          await app.evaluate(({BrowserWindow}, id) => BrowserWindow.fromId(id).setContentProtection(true), windowId)
          const result = await captureKit('sck-' + mode + '-protected-picker', mode)
          result.mode = mode
          result.controlFixtureFraction = control.fixtureFraction
          result.protectedWindowVisible = result.fixtureFraction > 0.1 || result.maxUnexpectedPixels > 0
          observations.push(result)
          console.log('ScreenCaptureKit observation: ' + JSON.stringify(result))
        }
        await fs.writeFile(path.join(output, 'sck-result.json'), JSON.stringify(observations, null, 2))
        assert(observations.every(result => !result.protectedWindowVisible), 'Protected content must be absent in every capture path and recorded frame')
      }
      await page.keyboard.press('Escape')
      await page.locator('#hint').hover()
      await page.getByRole('tooltip').waitFor({ state: 'visible' })
      assert(await screenshot('os-protected-tooltip') > 0.99, 'Tooltip must also be excluded by OS screenshot')
      await app.evaluate(({ BrowserWindow }, id) => {
        BrowserWindow.getAllWindows().filter(win => win.id !== id).forEach(win => win.destroy())
      }, windowId)
      console.log('OS screenshot: unprotected control visible; protected picker and tooltip excluded')
    }
    await page.keyboard.press('Escape')
    await page.locator('#modeSelect').selectOption('fast')
    await page.locator('#modeSelect').focus()
    await page.keyboard.press('Space')
    await page.keyboard.press('ArrowDown')
    await page.keyboard.press('Enter')
    assert.equal(await page.locator('#modeSelect').inputValue(), 'turbo', 'Keyboard selection remains functional')
    await page.mouse.move(5, 5)
    await page.locator('#hint').hover()
    await page.getByRole('tooltip').waitFor({ state: 'visible' })
    assert.equal(await page.getByRole('tooltip').textContent(), 'Private model availability details')
    await page.screenshot({ path: path.join(output, 'tooltip.png') })
    await page.keyboard.press('Escape')
    await page.getByRole('tooltip').waitFor({ state: 'hidden' })
    await page.locator('#hint').evaluate(el => { el.title = 'Updated availability'; })
    await page.locator('#hint').focus()
    await page.getByRole('tooltip').waitFor({ state: 'visible' })
    assert.equal(await page.getByRole('tooltip').textContent(), 'Updated availability')
    assert.equal(await page.locator('#hint').getAttribute('title'), null)
    assert.equal(await page.locator('#icon').getAttribute('aria-label'), 'Settings')
    await page.locator('#bottom').scrollIntoViewIfNeeded()
    await page.getByRole('tooltip').waitFor({ state: 'hidden' })
    await page.locator('#bottom').click()
    assert.equal(await page.locator('#bottom').evaluate(el => el.matches(':open')), true)
    await page.keyboard.press('Escape')
    await page.evaluate(() => {
      const select = document.createElement('select'); select.id = 'dynamic';
      select.innerHTML = '<option title="Private option detail">Added model</option><option disabled>Unavailable</option>';
      document.body.append(select)
    })
    assert.equal(await page.locator('#dynamic').evaluate(el => getComputedStyle(el).appearance), 'base-select')
    assert.equal(await page.locator('#dynamic option').first().getAttribute('title'), null)
    await page.reload()
    assert.equal(await page.locator('#modelSelect').evaluate(el => getComputedStyle(el).appearance), 'base-select')
    const protectedWindows = await app.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows().every(win => win.isContentProtected()))
    assert.equal(protectedWindows, true)
    console.log(JSON.stringify({ passed: true, output, checks: ['in-document model/mode picker', 'keyboard selection', 'native tooltip removal', 'hover/focus tooltip', 'Escape', 'dynamic controls', 'scroll', 'navigation', 'OS protection flag'] }, null, 2))
  } finally { if (app) await app.close() }
}
main().catch(error => { console.error(error); process.exitCode = 1 })
