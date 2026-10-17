const test = require('node:test');
const assert = require('node:assert/strict');
const { createRequire } = require('node:module');
// Resolve through the packages that consume these dependencies. Directly
// testing vendor source would miss a stale or broken npm override.
const globRequire = createRequire(require.resolve('micromatch'));
const nativeRequire = createRequire(require.resolve('@react-native-community/cli-doctor'));
const metroRequire = createRequire(require.resolve('metro'));
const braces = globRequire('braces');
const ip = nativeRequire('ip');

test('brace parsing rejects attacker-controlled recursive nesting', () => {
  assert.equal(globRequire('braces/package.json').name, '@ant/braces-safe');
  assert.throws(() => braces('{'.repeat(1000) + 'x' + '}'.repeat(1000)), /nesting/);
  assert.deepEqual(braces.expand('file{1..3}.txt'), ['file1.txt', 'file2.txt', 'file3.txt']);
  assert.deepEqual(braces.expand('{a,b}/{x,y}'), ['a/x', 'a/y', 'b/x', 'b/y']);
});

test('public IP classification fails closed for alternate and private addresses', () => {
  assert.equal(nativeRequire('ip/package.json').name, '@ant/ip-safe');
  for (const address of ['127.0.0.1', '127.1', '0177.0.0.1', '0x7f000001', '10.0.0.1',
    '169.254.169.254', '100.64.0.1', '::1', 'fc00::1', '::ffff:127.0.0.1', 'not-an-ip']) {
    assert.equal(ip.isPublic(address), false, address);
    assert.equal(ip.isPrivate(address), true, address);
  }
  assert.equal(ip.isPublic('8.8.8.8'), true);
  assert.equal(ip.isPublic('2001:4860:4860::8888'), true);
  assert.equal(typeof ip.address(), 'string');
});

test('Metro-compatible image sizing uses the patched parser', () => {
  assert.equal(metroRequire('image-size/package.json').name, '@ant/image-size-compat');
  const size = metroRequire('image-size');
  const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aG4sAAAAASUVORK5CYII=', 'base64');
  assert.equal(size(png).width, 1);
  assert.equal(size(png).height, 1);
  assert.equal(typeof size.imageSize, 'function');
});

test('navigation query parsing uses the bounded decoder with CommonJS compatibility', () => {
  const queryRequire = createRequire(require.resolve('query-string'));
  assert.equal(queryRequire('decode-uri-component/package.json').name, '@ant/decode-uri-compat');
  const query = require('query-string');
  assert.equal(query.parse('name=hello%20there').name, 'hello there');
  const decode = queryRequire('decode-uri-component');
  const started = performance.now();
  assert.equal(typeof decode('%C0'.repeat(4096)), 'string');
  assert.ok(performance.now() - started < 1000, 'Malformed URI decoding must remain bounded');
});
