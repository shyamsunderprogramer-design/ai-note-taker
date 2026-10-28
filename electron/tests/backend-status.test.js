const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
test('an existing healthy backend reports ready and starts monitoring', async () => {
  const source = fs.readFileSync(path.join(__dirname, '../main.js'), 'utf8');
  const start = source.indexOf('async function startBackend()');
  const end = source.indexOf('// IPC HANDLERS', start);
  const calls = [];
  const scope = {backendStopped: false, backendProcess: null, backendRestartAttempts: 2,
    isBackendRunning: async () => true, logger: {info() {}},
    notifyRendererBackendStatus: status => calls.push(status), startHealthCheck: () => calls.push('monitor')};
  await vm.runInNewContext(source.slice(start, end) + '\nstartBackend()', scope);
  assert.deepEqual(calls, ['ready', 'monitor']);
  assert.equal(scope.backendRestartAttempts, 0);
});
test('a new error cancels connected-status hiding and recovery clears restart action', () => {
  const source = fs.readFileSync(path.join(__dirname, '../../apps/web/app.js'), 'utf8');
  const start = source.indexOf('let backendStatusHideTimer');
  const end = source.indexOf('// Listen for backend status changes', start);
  const timers = new Map(); let id = 0;
  const classes = new Set();
  const element = {classList: {add: c => classes.add(c), remove: (...cs) => cs.forEach(c => classes.delete(c))}, style: {}};
  const scope = vm.createContext({backendStatusEl: element, backendStatusText: {},
    setTimeout: callback => {timers.set(++id, callback); return id}, clearTimeout: id => timers.delete(id)});
  vm.runInContext(source.slice(start, end), scope);
  vm.runInContext('updateBackendStatus("ready"); updateBackendStatus("error")', scope);
  assert.equal(timers.size, 0);
  assert.ok(classes.has('visible') && classes.has('error'));
  vm.runInContext('updateBackendStatus("dead"); updateBackendStatus("ready")', scope);
  assert.equal(element.onclick, null);
  assert.equal(element.style.cursor, '');
});

test('health monitoring avoids overlapping polls and requires repeated failure', async () => {
  const source = fs.readFileSync(path.join(__dirname, '../main.js'), 'utf8');
  const start = source.indexOf('function startHealthCheck()');
  const end = source.indexOf('function stopHealthCheck()', start);
  let tick, resolveProbe;
  const statuses = [];
  const scope = vm.createContext({
    backendHealthCheckInterval: null, backendHealthCheckInFlight: false,
    backendHealthFailures: 0, backendHealthGeneration: 0, backendStopped: false,
    backendStatus: 'ready', backendProcess: {}, backendRestartAttempts: 0,
    BACKEND_HEALTH_CHECK_INTERVAL_MS: 5000, logger: { info() {}, warn() {} },
    setInterval: fn => { tick = fn; return 1; },
    isBackendRunning: () => new Promise(resolve => { resolveProbe = resolve; }),
    notifyRendererBackendStatus: status => { statuses.push(status); scope.backendStatus = status; },
  });
  vm.runInContext(source.slice(start, end) + '\nstartHealthCheck()', scope);
  const first = tick();
  const resolver = resolveProbe;
  await tick();
  assert.equal(resolveProbe, resolver, 'overlapping health check started');
  resolveProbe(false); await first;
  assert.deepEqual(statuses, ['checking']);
  const second = tick(); resolveProbe(false); await second;
  assert.deepEqual(statuses, ['checking', 'error']);
  const recovery = tick(); resolveProbe(true); await recovery;
  assert.deepEqual(statuses, ['checking', 'error', 'ready']);
  assert.equal(scope.backendHealthFailures, 0);
});
