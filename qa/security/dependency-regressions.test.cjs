const test = require('node:test');
const assert = require('node:assert/strict');
const braces = require('../../vendor/braces-safe');
const ip = require('../../vendor/ip-safe');

test('brace parsing rejects attacker-controlled recursive nesting', () => {
  assert.throws(() => braces('{'.repeat(1000) + 'x' + '}'.repeat(1000)), /nesting/);
  assert.deepEqual(braces.expand('file{1..3}.txt'), ['file1.txt', 'file2.txt', 'file3.txt']);
  assert.deepEqual(braces.expand('{a,b}/{x,y}'), ['a/x', 'a/y', 'b/x', 'b/y']);
});

test('public IP classification fails closed for alternate and private addresses', () => {
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
  const size = require('../../vendor/image-size-compat');
  const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aG4sAAAAASUVORK5CYII=', 'base64');
  assert.equal(size(png).width, 1);
  assert.equal(size(png).height, 1);
  assert.equal(typeof size.imageSize, 'function');
});
