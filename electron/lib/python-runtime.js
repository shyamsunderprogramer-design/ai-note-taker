const fs = require('node:fs');
const path = require('node:path');

function pythonExecutable({ packaged, resourcesPath, appDirectory, platform = process.platform }) {
  const windows = platform === 'win32';
  if (packaged) {
    const executable = path.join(resourcesPath, 'python', windows ? 'python.exe' : 'bin/python3');
    fs.accessSync(executable, fs.constants.X_OK);
    return executable;
  }
  for (const root of [path.join(appDirectory, '..'), path.join(appDirectory, '../..')]) {
    const executable = path.join(root, 'AINT_Venv', windows ? 'Scripts/python.exe' : 'bin/python');
    try {
      fs.accessSync(executable, fs.constants.X_OK);
      return executable;
    } catch { /* Try the next development environment. */ }
  }
  return windows ? 'python' : 'python3';
}

module.exports = { pythonExecutable };
