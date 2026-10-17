const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const { pythonExecutable } = require('../lib/python-runtime');

for (const platform of ['darwin', 'linux', 'win32']) {
  test(`packaged ${platform} resolves its relocated interpreter and never falls back to system Python`, () => {
    const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'ant-runtime-'));
    try {
      const options = { packaged: true, resourcesPath: directory, platform };
      assert.throws(() => pythonExecutable(options), /ENOENT/);
      const interpreter = path.join(directory, 'python', platform === 'win32' ? 'python.exe' : 'bin/python3');
      fs.mkdirSync(path.dirname(interpreter), { recursive: true });
      fs.writeFileSync(interpreter, '', { mode: 0o755 });
      assert.equal(pythonExecutable(options), interpreter);
      const relocated = path.join(directory, 'relocated resources');
      fs.mkdirSync(relocated);
      fs.renameSync(path.join(directory, 'python'), path.join(relocated, 'python'));
      assert.equal(pythonExecutable({ ...options, resourcesPath: relocated }),
        path.join(relocated, path.relative(directory, interpreter)));
    } finally {
      fs.rmSync(directory, { recursive: true, force: true });
    }
  });
}

test('development can use system Python when no project environment exists', () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'ant-dev-runtime-'));
  try {
    assert.equal(pythonExecutable({ packaged: false, appDirectory: path.join(directory, 'repo/electron'), platform: 'linux' }), 'python3');
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});
