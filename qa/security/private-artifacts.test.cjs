'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const { artifactDirectory, readPrivateJson } = require('./private-artifacts.cjs');

test('artifact runs are distinct private directories and reject symlink reuse', () => {
  const first = artifactDirectory('ant-artifact-test-');
  const second = artifactDirectory('ant-artifact-test-');
  try {
    assert.notEqual(first, second);
    assert.equal(artifactDirectory('unused-', first), first);
    if (typeof process.getuid === 'function') {
      assert.equal(fs.statSync(first).mode & 0o077, 0);
      fs.chmodSync(second, 0o755);
      assert.throws(() => artifactDirectory('unused-', second), /private directory/);
    }
    const link = path.join(first, 'link');
    fs.symlinkSync(second, link, process.platform === 'win32' ? 'junction' : 'dir');
    assert.throws(() => artifactDirectory('unused-', link), /private directory/);
  } finally {
    fs.rmSync(first, { recursive: true });
    fs.rmSync(second, { recursive: true });
  }
});

test('credentials reject public files and symlinks while reading a private regular file', () => {
  const directory = artifactDirectory('ant-credential-test-');
  const filename = path.join(directory, 'fixture.json');
  try {
    fs.writeFileSync(filename, JSON.stringify({ username: 'synthetic' }), { flag: 'wx', mode: 0o600 });
    assert.deepEqual(readPrivateJson(filename), { username: 'synthetic' });
    if (typeof process.getuid === 'function') {
      fs.chmodSync(filename, 0o644);
      assert.throws(() => readPrivateJson(filename), /private file/);
      fs.chmodSync(filename, 0o600);
      const link = path.join(directory, 'link.json');
      fs.symlinkSync(filename, link);
      assert.throws(() => readPrivateJson(link));
    }
  } finally {
    fs.rmSync(directory, { recursive: true });
  }
});
