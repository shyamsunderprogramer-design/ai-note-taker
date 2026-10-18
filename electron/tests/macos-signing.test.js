const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const test = require('node:test');
const signRuntime = require('../scripts/sign-runtime.cjs').default;

const team = 'TESTTEAM12';
const identity = { name: `Developer ID Application: ANT Test (${team})`, hash: 'A'.repeat(40) };

function fixture(t, release = true) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'ant-signing-'));
  t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
  const resources = path.join(directory, 'ANT Test.app/Contents/Resources');
  fs.mkdirSync(path.join(resources, 'python/bin'), { recursive: true });
  fs.mkdirSync(path.join(resources, 'python/lib'), { recursive: true });
  const macho = Buffer.from('cffaedfe000000000000000000000000', 'hex');
  fs.writeFileSync(path.join(resources, 'python/bin/python3.12'), macho);
  fs.writeFileSync(path.join(resources, 'python/lib/extension.so'), macho);
  fs.symlinkSync('python3.12', path.join(resources, 'python/bin/python3'));
  fs.writeFileSync(path.join(resources, 'python/lib/data.txt'), 'not executable');
  fs.writeFileSync(path.join(resources, 'python/lib/archive.a'), '!<arch>\n');
  fs.writeFileSync(path.join(resources, 'python/lib/short'), 'x');
  fs.writeFileSync(path.join(resources, 'audiotee'), macho);
  const config = release
    ? { notarize: true, hardenedRuntime: true, type: 'distribution', identity: '', entitlements: 'assets/entitlements.mac.plist' }
    : { notarize: false, hardenedRuntime: false, identity: '-' };
  const context = {
    electronPlatformName: 'darwin', appOutDir: directory,
    packager: {
      appInfo: { productFilename: 'ANT Test' }, projectDir: path.resolve(__dirname, '..'),
      forceCodeSigning: release, platformSpecificBuildOptions: config,
      codeSigningInfo: { value: Promise.resolve({ keychainFile: '/temporary/signing.keychain' }) },
      helper: { findSigningIdentity: async (...args) => {
        assert.deepEqual(args, [false, false, '', '/temporary/signing.keychain', config]);
        return identity;
      } },
    },
  };
  const previous = process.env.APPLE_TEAM_ID;
  process.env.APPLE_TEAM_ID = team;
  t.after(() => {
    if (previous === undefined) delete process.env.APPLE_TEAM_ID;
    else process.env.APPLE_TEAM_ID = previous;
  });
  return context;
}

test('distribution signs only real runtime binaries, with the outer app identity and secure timestamp', async t => {
  const context = fixture(t);
  const signed = [];
  await signRuntime(context, (command, args) => {
    assert.equal(command, '/usr/bin/codesign');
    assert.equal(args[args.indexOf('--sign') + 1], identity.hash);
    assert.equal(args[args.indexOf('--options') + 1], 'runtime');
    assert.equal(args[args.indexOf('--keychain') + 1], '/temporary/signing.keychain');
    assert.ok(args.includes('--timestamp'));
    assert.ok(!args.includes('--timestamp=none'));
    assert.ok(fs.existsSync(args[args.indexOf('--entitlements') + 1]));
    signed.push(path.basename(args.at(-1)));
  });
  assert.deepEqual(signed.sort(), ['audiotee', 'extension.so', 'python3.12']);
});

test('local builds retain ad-hoc runtime signing without consulting Apple credentials', async t => {
  const context = fixture(t, false);
  context.packager.helper.findSigningIdentity = () => { throw new Error('Unexpected identity lookup'); };
  let calls = 0;
  await signRuntime(context, (_command, args) => {
    assert.deepEqual(args.slice(0, 4), ['--force', '--sign', '-', '--timestamp=none']);
    calls++;
  });
  assert.equal(calls, 3);
});

for (const invalid of [null, { name: 'Apple Development: Test', hash: identity.hash }, { name: 'Developer ID Application: Test (OTHERTEAM1)', hash: identity.hash }]) {
  test(`distribution refuses missing, development or wrong-team identity: ${invalid?.name || 'missing'}`, async t => {
    const context = fixture(t);
    context.packager.helper.findSigningIdentity = async () => invalid;
    await assert.rejects(signRuntime(context, () => assert.fail('Must not sign with an invalid identity')), /Developer ID|APPLE_TEAM_ID/);
  });
}

test('credential import and codesign errors stop the release without ad-hoc fallback', async t => {
  const context = fixture(t);
  context.packager.codeSigningInfo = { get value() { throw new Error('certificate import failed'); } };
  await assert.rejects(signRuntime(context, () => assert.fail('Must not sign')), /certificate import failed/);
  context.packager.codeSigningInfo = { value: Promise.resolve({ keychainFile: '/temporary/signing.keychain' }) };
  await assert.rejects(signRuntime(context, () => { throw new Error('timestamp server unavailable'); }), /timestamp server unavailable/);
});

test('notarized builds refuse disabled Hardened Runtime', async t => {
  const context = fixture(t);
  context.packager.platformSpecificBuildOptions.hardenedRuntime = false;
  await assert.rejects(signRuntime(context, () => assert.fail('Must not sign')), /Hardened Runtime/);
});

test('release configuration rejects missing credentials before building and requires distribution signing', () => {
  const configuration = path.resolve(__dirname, '../electron-builder.mac-release.cjs');
  const environment = { ...process.env };
  for (const name of ['CSC_LINK', 'CSC_KEY_PASSWORD', 'APPLE_ID', 'APPLE_APP_SPECIFIC_PASSWORD', 'APPLE_TEAM_ID']) delete environment[name];
  const missing = spawnSync(process.execPath, [configuration], { env: environment, encoding: 'utf8' });
  assert.notEqual(missing.status, 0);
  assert.match(missing.stderr, /macOS releases require signing and notarization credentials/);
  Object.assign(environment, { CSC_LINK: 'fixture-certificate', CSC_KEY_PASSWORD: 'fixture-password', APPLE_ID: 'release@example.com', APPLE_APP_SPECIFIC_PASSWORD: 'fixture-app-password', APPLE_TEAM_ID: team });
  const configured = spawnSync(process.execPath, ['-e', 'console.log(JSON.stringify(require(process.argv[1])))', configuration], { env: environment, encoding: 'utf8' });
  assert.equal(configured.status, 0, configured.stderr);
  const { mac, forceCodeSigning } = JSON.parse(configured.stdout);
  assert.equal(forceCodeSigning, true);
  assert.equal(mac.type, 'distribution');
  assert.equal(mac.hardenedRuntime, true);
  assert.equal(mac.notarize, true);
  assert.notEqual(mac.identity, '-');
  assert.equal(require('../package.json').build.mac.identity, '-');
});
